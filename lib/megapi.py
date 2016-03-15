import serial
import sys,time
import signal
from time import ctime,sleep
import glob,struct
from multiprocessing import Process,Manager,Array
import threading

class mSerial():
	ser = None
	def __init__(self):
		print self

	def start(self):
		self.ser = serial.Serial('/dev/ttyAMA0',115200,timeout=0)
	
	def device(self):
		return self.ser

	def serialPorts(self):
		if sys.platform.startswith('win'):
			ports = ['COM%s' % (i + 1) for i in range(256)]
		elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
			ports = glob.glob('/dev/tty[A-Za-z]*')
		elif sys.platform.startswith('darwin'):
			ports = glob.glob('/dev/tty.*')
		else:
			raise EnvironmentError('Unsupported platform')
		result = []
		for port in ports:
			s = serial.Serial()
			s.port = port
			s.close()
			result.append(port)
		return result

	def writePackage(self,package):
		self.ser.write(package)
		sleep(0.01)

	def read(self):
		return self.ser.read()

	def isOpen(self):
		return self.ser.isOpen()

	def inWaiting(self):
		return self.ser.inWaiting()

	def close(self):
		self.ser.close()
		

class MegaPi():
	def __init__(self):
		print "init MegaPi"
		signal.signal(signal.SIGINT, self.exit)
		self.manager = Manager()
		self.__selectors = self.manager.dict()
		self.buffer = []
		self.bufferIndex = 0
		self.isParseStart = False
		self.exiting = False
		self.isParseStartIndex = 0
		
	def start(self):
		self.device = mSerial()
		self.device.start()
		sys.excepthook = self.excepthook
		th = threading.Thread(target=self.__onRead,args=(self.onParse,))
		th.start()
		
	def excepthook(self, exctype, value, traceback):
		self.close()
		
	def close(self):
		self.device.close()
		
	def exit(self, signal, frame):
		self.exiting = True
		sys.exit(0)
		
	def __onRead(self,callback):
		while 1:
			if(self.exiting==True):
				break
			try:	
				if self.device.isOpen()==True:
					n = self.device.inWaiting()
					for i in range(n):
						r = ord(self.device.read())
						callback(r)
					sleep(0.01)
				else:	
					sleep(0.5)
			except Exception,ex:
				print str(ex)
				self.close()
				sleep(1)
				
	def __writePackage(self,pack):
		self.device.writePackage(pack)
		
	def __writeRequestPackage(self,deviceId,port,callback):
		extId = ((port<<4)+deviceId)&0xff
		self.__doCallback(extId,callback)
		self.__writePackage(bytearray([0xff,0x55,0x4,extId,0x1,deviceId,port]))
	
	def digitalRead(self,pin,callback):
		self.__writeRequestPackage(0x1e,pin,callback)
		
	def analogRead(self,pin,callback):
		self.__writeRequestPackage(0x1f,pin,callback)	
	
	def sevenSegmentDisplay(self,port,display):
		self.__writePackage(bytearray([0xff,0x55,0x8,0x0,0x2,0x9,port]+self.float2bytes(display)))
			
	def lightSensorRead(self,port,callback):
		self.__writeRequestPackage(4,port,callback)
	
	def ultrasonicSensorRead(self,port,callback):
		self.__writeRequestPackage(1,port,callback)
		
	def lineFollowerRead(self,port,callback):
		self.__writeRequestPackage(17,port,callback)
		
	def soundSensorRead(self,port,callback):
		self.__writeRequestPackage(7,port,callback)
		
	def pirMotionSensorRead(self,port,callback):
		self.__writeRequestPackage(15,port,callback)
		
	def potentiometerRead(self,port,callback):
		self.__writeRequestPackage(4,port,callback)
		
	def limitSwitchRead(self,port,callback):
		self.__writeRequestPackage(21,port,callback)
		
	def temperatureRead(self,port,callback):
		self.__writeRequestPackage(2,port,callback)
		
	def touchSensorRead(self,port,callback):
		self.__writeRequestPackage(15,port,callback)
		
	def humitureSensorRead(self,port,type,callback):
		deviceId = 23;
		extId = ((port<<4)+deviceId)&0xff
		self.__doCallback(extId,callback)
		self.__writePackage(bytearray([0xff,0x55,0x5,extId,0x1,deviceId,port,type]))
		
	def joystickRead(self,port,axis,callback):
		deviceId = 5;
		extId = ((port<<4)+deviceId)&0xff
		self.__doCallback(extId,callback)
		self.__writePackage(bytearray([0xff,0x55,0x5,extId,0x1,deviceId,port,axis]))
		
	def gasSensorRead(self,port,callback):
		self.__writeRequestPackage(25,port,callback)
		
	def buttonRead(self,port,callback):
		self.__writeRequestPackage(22,port,callback)
		
	def gyroRead(self,extID,callback):
		self.__writeRequestPackage(6,extID,callback)
		
	def digitalWrite(self,pin,level):
		self.__writePackage(bytearray([0xff,0x55,0x5,0x0,0x2,0x1e,pin,level]))
		
	def pwmWrite(self,pin,pwm):
		self.__writePackage(bytearray([0xff,0x55,0x5,0x0,0x2,0x20,pin,pwm]))
		
	def motorRun(self,port,speed):
		self.__writePackage(bytearray([0xff,0x55,0x6,0x0,0x2,0xa,port]+self.short2bytes(speed)))

	def motorMove(self,leftSpeed,rightSpeed):
		self.__writePackage(bytearray([0xff,0x55,0x7,0x0,0x2,0x5]+self.short2bytes(-leftSpeed)+self.short2bytes(rightSpeed)))
		
	def servoRun(self,port,slot,angle):
		self.__writePackage(bytearray([0xff,0x55,0x6,0x0,0x2,0xb,port,slot,angle]))

	def encoderMotorRun(self,port,speed):
		self.__writePackage(bytearray([0xff,0x55,0x6,0,0x2,62,port]+self.short2bytes(speed)))
		
	def encoderMotorMove(self,port,distance):
		self.__writePackage(bytearray([0xff,0x55,0x7,0,0x2,61,port,0x0]+self.short2bytes(distance)))
		
	def encoderMotorMoveTo(self,port,position):
		self.__writePackage(bytearray([0xff,0x55,0x7,0,0x2,61,port,0x1]+self.short2bytes(position)))
		
	def stepperMotorRun(self,port,speed):
		self.__writePackage(bytearray([0xff,0x55,0x7,0,0x2,40,port,0x0]+self.short2bytes(speed)))
		
	def stepperMotorMove(self,port,distance):
		self.__writePackage(bytearray([0xff,0x55,0x7,0,0x2,40,port,0x1]+self.short2bytes(distance)))
		
	def stepperMotorMoveTo(self,port,position):
		self.__writePackage(bytearray([0xff,0x55,0x7,0,0x2,40,port,0x2]+self.short2bytes(position)))
		
	def rgbLedDisplay(self,port,slot,index,red,green,blue):
		self.__writePackage(bytearray([0xff,0x55,0x9,0x0,0x2,0x8,port,slot,index,red,green,blue]))

	def ledMatrixDisplay(self,port,buffer):
		self.__writePackage(bytearray([0xff,0x55,12,0,0x2,41,port]+buffer))
		
	def shutterDo(self,extID,port,method):
		self.__writePackage(bytearray([0xff,0x55,0x5,0,0x3,20,port,method]))
		
	def onParse(self, byte):
		position = 0
		value = 0	
		self.buffer+=[byte]
		bufferLength = len(self.buffer)
		if bufferLength >= 2:
			if (self.buffer[bufferLength-1]==0x55 and self.buffer[bufferLength-2]==0xff):
				self.isParseStart = True
				self.isParseStartIndex = bufferLength-2	
			if (self.buffer[bufferLength-1]==0xa and self.buffer[bufferLength-2]==0xd and self.isParseStart==True):			
				self.isParseStart = False
				position = self.isParseStartIndex+2
				extID = self.buffer[position]
				position+=1
				type = self.buffer[position]
				position+=1
				# 1 byte 2 float 3 short 4 len+string 5 double
				if type == 1:
					value = self.buffer[position]
				if type == 2:
					value = self.readFloat(position)
					if(value<-255 or value>1023):
						value = 0
				if type == 3:
					value = self.readShort(position)
				if type == 4:
					value = self.readString(position)
				if type == 5:
					value = self.readDouble(position)
				if(type<=5):
					self.responseValue(extID,value)
				self.buffer = []

	def readFloat(self, position):
		v = [self.buffer[position], self.buffer[position+1],self.buffer[position+2],self.buffer[position+3]]
		return struct.unpack('<f', struct.pack('4B', *v))[0]
	def readShort(self, position):
		v = [self.buffer[position], self.buffer[position+1]]
		return struct.unpack('<h', struct.pack('2B', *v))[0]
	def readString(self, position):
		l = self.buffer[position]
		position+=1
		s = ""
		for i in Range(l):
			s += self.buffer[position+i].charAt(0)
		return s
	def readDouble(self, position):
		v = [self.buffer[position], self.buffer[position+1],self.buffer[position+2],self.buffer[position+3]]
		return struct.unpack('<f', struct.pack('4B', *v))[0]

	def responseValue(self, extID, value):
		self.__selectors["callback_"+str(extID)](value)
		
	def __doCallback(self, extID, callback):
		self.__selectors["callback_"+str(extID)] = callback

	def float2bytes(self,fval):
		val = struct.pack("f",fval)
		return [ord(val[0]),ord(val[1]),ord(val[2]),ord(val[3])]

	def short2bytes(self,sval):
		val = struct.pack("h",sval)
		return [ord(val[0]),ord(val[1])]