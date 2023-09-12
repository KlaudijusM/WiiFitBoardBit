# Wii Fit Board Bit

## Project goals

This project aims to utilize the [Wii Balance board](https://en.wikipedia.org/wiki/Wii_Balance_Board) as a smart scale to measure weight and log it on a FitBit account. This software is intended to be used on the Raspberry Pi 4 (but can be used on other versions) to track weight from day to day.

## Previous work

Quite a few tutorials exist for tracking weight using the Wii Balance board and a Raspberry pi. While the most popular tutorial by [Greg Nichols](https://www.zdnet.com/article/diy-build-a-hackable-weight-tracking-scale-with-a-sense-of-humor-using-raspberry-pi/) does the job just fine it requires the red "sync" button in the battery compartment to be pressed each and every time, which is not ideal. This repo is based on the code provided by [Marcel Bieberbach](https://github.com/chaosbiber/wiiweigh) and the previous work of [Zachary Burchill](https://www.zachburchill.ml/bluetooth_scale_intro/) who addresses all the problems that others don't. 

## Requirements

To run ```wiifitboardbit```, the following is required:
- Linux (preferably a [Debian](https://www.debian.org/) based system).
- A device with a bluetooth adapter.
- [Python 2](https://www.python.org)
- [Bluez 5](http://www.bluez.org/)
- [XWiimote](https://github.com/dvdhrm/xwiimote) open-source driver.
- [XWiimote-bindings](https://github.com/dvdhrm/xwiimote-bindings) XWiimote library bindings.


## Setup

Start of with installing Python 2 and Bluez 5 if you don't have it:
```
sudo apt-get install python2 bluez
```

### XWiimote and XWiimote-Bindings

Configuring [XWiimote](https://github.com/dvdhrm/xwiimote) and [XWiimote-bindings](https://github.com/dvdhrm/xwiimote-bindings) from scratch. 

To configure and install XWiimote and XWiimote-bindings you should first install a few extra dependencies:
```
sudo apt-get install python-dbus git autoconf libtool libudev-dev libncurses5-dev swig python-dev python-numpy libcairo2-dev libgirepository1.0-dev libssl-dev
```
Afterwards you can clone the repos, run _autogen.sh_ (you might need to use the _/usr_ prefix flag or [load path](https://askubuntu.com/a/684373) with ```export LD_LIBRARY_PATH=/usr/local/lib```) and install the driver with its bindings.
```
git clone https://github.com/dvdhrm/xwiimote.git
git clone https://github.com/dvdhrm/xwiimote-bindings.git
cd xwiimote
./autogen.sh [--prefix=/usr]
make
sudo make install
cd ../xwiimote-bindings
./autogen.sh [--prefix=/usr]
make
sudo make install
cd ..
```


## Balance board pairing

### Pairing the Wii Balance board for the first time

An initial setup is required to pair the Wii Balance board with the device you're planning to run ```wiifitboardbit``` on. This pairing allows to use the front button on the Wii Balance board to initialize the weight tracking later.

1. Start _bluetoothctl_ ```sudo bluetoothctl``` and then in the bluetooth setup screen:
2. ```power on```
3. ```agent on```
4. ```scan on``` this will start looking for available bluetooth devices. Press the red "sync" button on the bottom of the balance board and take note of the MAC address of the Wii Balance board.
5. ```pair <MAC of the Wii Balance board>``` this only pairs to the device but doesn't connect. The next command (_connect_) should be executed immediately after pairing since there's only a short timeout.
6. ```connect <MAC of the Wii Balance board>```
7. ```trust <MAC of the Wii Balance board>```

After pairing and establishing trust we can disconnect, stop the scan and exit the bluetooth setup screen:

8. ```disconnect <MAC of the Wii Balance board>```
9. ```scan off```
10. ```exit```

So everything should look like this:
```
power on
Changing power on succeeded


agent on
Agent has been registered/Agent is already registered


scan on
Discovery started
...
[NEW] Device XX:XX:XX:XX:XX:XX XX-XX-XX-XX-XX-XX
...
[CHG] Device XX:XX:XX:XX:XX:XX Name: Nintendo RVL-WBC-01
[CHG] Device XX:XX:XX:XX:XX:XX Alias: Nintendo RVL-WBC-01


pair XX:XX:XX:XX:XX:XX
Attempting to pair with XX:XX:XX:XX:XX:XX
...
Pairing successful


connect XX:XX:XX:XX:XX:XX
Attempting to connect to XX:XX:XX:XX:XX:XX
Connection successful


trust XX:XX:XX:XX:XX:XX
[CHG] Device XX:XX:XX:XX:XX:XX Trusted: yes
Changing XX:XX:XX:XX:XX:XX trust succeeded


disconnect XX:XX:XX:XX:XX:XX 
Attempting to disconnect from XX:XX:XX:XX:XX:XX
...
Successful disconnected


scan off
Discovery stopped


exit
```


## Running WiiFitBoardBit

You should firs make sure that all of the requirements are met. You can install all of the requirements by navigating to the WiiFitBoardBit folder and running:
```pip install -r requirements.txt```

If you had to configure XWiimote and XWiimote-bindings with the _prefix_ flag you'll need to specify [additional info](https://github.com/dvdhrm/xwiimote-bindings/issues/12#issuecomment-549531955):

```sudo LD_LIBRARY_PATH=<prefix>/lib PYTHONPATH=<prefix>/lib/python2.7/site-packages python ./main.py```

Otherwise you can just launch the application with:

```python ./main.py```

If you managed to pair the WiiFit Board in the steps described above you shouldn't have any problems running the ```main.py``` file, clicking the power button on the board and stepping on. After a few seconds the board (indicated by the light on it) should turn off and the weight should be logged in a CSV file.

## How this works

As described above, the main source code that handles the weight logging was cloned from this repository of [Marcel](https://github.com/chaosbiber/wiiweigh). It was slightly adjusted and optimised to decrease the time to log the weight (decreasing the precision) and to store the data in a CSV file.

Furthermore I've added an API integration with FitBit that checks the stored data every 30 seconds by default and updates any non-synced data. To enable this integration I suggest you check out the ```config.py``` file and register a personal FitBit app. The reason why you need to register an app is to have a direct integration between FitBit and your local clone so that the data is not going through some third party server/app (that I would have to host). This FitBit integration is purely optional but if you use a FitBit device it's handy.

## Future work, known issues and final thoughts

I'm not planning to make any changes to this as long as it works. I've built this for my own personal needs and to help others that might want to repurpose their old WiiFit Board. It shouldn't be hard to adjust this repo to sync with Google Health or other health data tracking providers.

The code is not the best. XWiiMote still runs on Python 2 and the build process of it is problematic. The communication with C libraries is also annoying. Python doesn't seem like the best solution for what is required. If I would have to do it all again I would choose a different programming language for this project.

If you face any issues or want to discuss some ideas - you can contact me directly via [e-mail](mailto:klaudijus.miniotas@gmail.com) or open up an issue through GitHub.
