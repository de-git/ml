from controller import *
import os,re,time,random,math

class EpuckFunctions (DifferentialWheels):
    max_wheel_speed = 1000
    num_dist_sensors = 8
    encoder_resolution = 159.23 # for wheel encoders
    tempo = 0.5  # Upper velocity bound = Fraction of the robot's maximum velocity = 1000 = 1 wheel revolution/sec  
    wheel_diameter = 4.1 # centimeters
    axle_length = 5.3 # centimeters
    timestep_duration = 200/1000 # Real-time seconds per timestep

    def basic_setup(self, timestep = 200, tempo = 1.0):
        self.timestep = timestep
        self.tempo = tempo
        self.enableEncoders(self.timestep)
        self.camera = self.getCamera('camera')
        self.camera.enable(4*self.timestep)
        self.dist_sensor_values = [0 for i in range(self.num_dist_sensors)]
        self.dist_sensors = [self.getDistanceSensor('ps'+str(x)) for x in range(self.num_dist_sensors)]  # distance sensors
        self.camera_sample_size = [8,8] # x,y sample size in pixels
        self.camera_sample_array_length = self.camera_sample_size[0] * self.camera_sample_size [1] * 3
        map((lambda s: s.enable(self.timestep)), self.dist_sensors) # Enable all distance sensors
        self.update_proximities()
        self.step(self.timestep)
        self.emitter = self.getEmitter("emitter");
        self.receiver = self.getReceiver("receiver");
        self.gps = self.getGPS("gps");
        self.gps.enable(timestep)
        self.compass = self.getCompass("compass");
        self.compass.enable(timestep)
        self.receiver.enable(self.timestep)
        self.receiver.setChannel(1)
        self.emitter.setChannel(2)
        self.current_x = None
        self.current_y = None

    def move_wheels(self, speeds = [1,1], wheels=["L","R"]):
        left = None
        right = None
        for i in range(0,len(speeds)):
            if wheels[i] == "L":
                left = speeds[i]
            else:
                right = speeds[i]
        if left is None:
            left = self.getLeftSpeed()/self.max_wheel_speed
        if right is None:
            right = self.getRightSpeed()/self.max_wheel_speed
#        if left >= 1.0:
#            left = 0.9
#        if right >= 1.0:
#            right = 0.9
        self.setSpeed(int(left*self.max_wheel_speed),int(right*self.max_wheel_speed))

    def get_coordinates(self):
        gps_sensors = self.gps.getValues();
        return [gps_sensors[0], gps_sensors[2]]

    def get_compass_heading_in_grad(self):
        compass_values = self.compass.getValues();
        # subtract math.pi/2 (90) so that the heading is 0 facing 'north' (given x going from left to right) 
        rad = math.atan2(compass_values[0], compass_values[2]) - (math.pi / 2);
        if (rad < -math.pi):
            rad = rad + (2 * math.pi)
        return rad / math.pi * 180.0

    def get_random_wheel(self):
        return random.choice(["L","R"])
        

    def update_current_coordinates(self,d_str):
        r = re.match('(.*),(.*)',d_str)
        self.current_x = float(r.group(1))
        self.current_y = float(r.group(2))

    def update_proximities(self):
        for i in range(self.num_dist_sensors):
            self.dist_sensor_values[i] = self.normalise_value(self.dist_sensors[i].getValue())
        return self.dist_sensor_values

    def normalise_value(self,value):
        if value > 250:
            value = 250
        return value

    def get_random_proximity_sensor(self):
        return random.randint(0,len(self.dist_sensors)-1)

    def get_proximity_sensor_value(self,s):
        value = self.dist_sensor_values[s]
        if value > 1000:
            value = 1000.0
        if value < 50:
            value = 0
        return value / 1000.0

    def get_multi_sensor_value(self,s):
        if s < len(self.dist_sensor_values):
            return self.get_proximity_sensor_value(s)
        elif s >= len(self.dist_sensor_values) and s < (len(self.dist_sensors)+self.camera_sample_array_length):
            # normalised by /255
            return self.current_snapshot[s-len(self.dist_sensor_values)]/255.0
        elif s == (len(self.dist_sensors)+self.camera_sample_array_length):
            return self.current_x
        elif s == (len(self.dist_sensors)+self.camera_sample_array_length) + 1:
            return self.current_y


    def get_random_multi_sensor(self):
        if random.random() < 0.25:
            return random.randint(0,(len(self.dist_sensors)-1))
        else:
            return random.randint(len(self.dist_sensors),len(self.dist_sensors)+self.camera_sample_array_length-1)

    def snapshot(self, show = False, sampled= True):
        if sampled:
            im = self.get_sampled_image()
        else:
            im = self.get_image()
            if show:
                im.save('test.bmp')
        self.current_snapshot = im
        return im

    def get_image(self):
        strImage=self.camera.getImageArray()
        im = Image.new('RGB', (self.camera.getWidth(), self.camera.getHeight()))
        c = []
        for i,a in enumerate(strImage):
            for j,b in enumerate(a):
                im.putpixel((i,j),(b[0],b[1],b[2]))
        return im

    def get_sampled_image(self):
        strImage=self.camera.getImageArray()
        im = []
        for columns in [0,7,14,21,29,37,44,51]:
            for rows in [0,5,10,16,22,28,33,38]:
                for colour in [0,1,2]:
                    im.append(strImage[columns][rows][colour])
        return im

    def avg_rgb(self,image):
        x,y = (len(image),len(image[0]))
        total = float(x*y)
        sum_r, sum_g, sum_b = 0.0, 0.0, 0.0
        for i in range(x):
            for j in range(y):
                # print "image[i][j]:",image[i][j]
                r,g,b = image[i][j][0],image[i][j][1],image[i][j][2]
                sum_r, sum_g, sum_b = sum_r + r, sum_g + g, sum_b + b
        return [sum_r/total, sum_g/total, sum_b/total]

    def get_average_intensity_in_grids(self):
        image = self.camera.getImageArray()
        for x in range(0,len(image)):
            image[x].append(image[x][-1])
        grids = self.get_five_by_five_grids(image)
        avrgd = []
        for i,g in enumerate(grids):
            intensities = self.avg_rgb(g)
            avrgd.append(sum(intensities)/len(intensities))
        return avrgd

    def get_five_by_five_grids(self,data,patch_size=8):
        patches = []
        for i in range(5):
            for j in range(5):
                patch = []
                for col in range(i*patch_size,i*patch_size+patch_size):
                    whole_row = []
                    for row in range(j*patch_size,j*patch_size+patch_size):
                        whole_row.append(data[col][row])
                    patch.append(whole_row)
                patches.append(patch)
        return patches

    def get_camera_image(self):
        "used to pass images to atoms"
        return self.current_snapshot

    def get_sampled_camera_image(self):
        "used to pass images to atoms"
        return self.current_snapshot

    def do_actual_spin(self,speed=1.0,direction = "cw"):
        if direction == "cw":
            self.setSpeed(speed*self.max_wheel_speed,
                -speed*self.max_wheel_speed)
        else:
            self.setSpeed(-speed*self.max_wheel_speed,
                speed*self.max_wheel_speed)

    def do_actual_move(self,speed_left=1.0,speed_right=None):
        if speed_right is None:
            speed_right = speed_left
        else:
            self.setSpeed(speed_left*self.max_wheel_speed,speed_right*self.max_wheel_speed)

    def stop_moving(self):
        self.setSpeed(0,0)