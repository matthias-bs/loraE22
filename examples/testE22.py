# Simple test program for loraE22 configuration

from loraE22 import ebyteE22

M0pin = 25
M1pin = 26
AUXpin = 14


e22 = ebyteE22(M0pin, M1pin, AUXpin, Port='U2', Address=0x0001, Channel=0x04, debug=False)

res = e22.start()
print("E22 start():", res)

res = e22.getConfig()
print("E22 getConfig(): ", res)

res = e22.showPID()
print("E22 showPID(): ", res)

e22.config['address'] = 0xDEAD
e22.config['channel'] = 0x55
e22.config['netid']   = 0xAA
res = e22.setConfig('setConfigPwrDwnNoSave')
print("E22 setConfig('setConfigPwrDwnNoSave'): ", res)

res = e22.getConfig()
print("E22 getConfig(): ", res)

e22.config['address'] = 0x0000
e22.config['channel'] = 0x00
e22.config['netid']   = 0x00
res = e22.setConfig('setConfigPwrDwnSave')
print("E22 setConfig('setConfigPwrDwnSave'): ", res)

res = e22.getConfig()
print("E22 getConfig(): ", res)


e22.stop()

