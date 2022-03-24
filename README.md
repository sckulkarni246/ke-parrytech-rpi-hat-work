# Kickstart Embedded - Parry Tech SIM7600EI RPi Hat Evaluation

**!!! THIS IS A WORK-IN-PROGRESS !!!**

## Objectives


1. To achieve AWS-IoT MQTT communication using Microchip ATECC608-TNGTLS as the identity provider to the AWS IoT cloud
2. The connection to cloud is done using Parry Tech's SIM7600EI based Raspberry Pi hat

## Major milestones

1. &#9989; Enable PPP-link with SIM7600EI on Raspberry Pi
2. &#9989; Build and test Microchip's cryptoauthlib on Raspberry Pi with PKCS11 support enabled
3. &#9989; Enroll ATECC608-TNGTLS to AWS IoT cloud account
4. &#10060; Use AWS IoT SDK (C or Python) with PKCS11 support to perform pub-sub
5. &#10060; Achieve two-way communication between Raspberry Pi and AWS dashboard/GUI/CLI with node

##  Software 
- Raspberry Pi Buster (32-bit)
- Microchip Cryptoauthlib (https://github.com/MicrochipTech/cryptoauthlib) tag -> v3.3.3
- Required apt packages: cmake, cmake-gui, openssl, libssl-dev, libengine-pkcs11-openssl1.1, autoconf, libtool, gnutls-bin 
- AWS account

## Hardware
- Raspberry Pi 3B
- Parry Tech SIM7600EI RPi Hat
- 5V 2.5A Power Supply Adapter
- Antenna for LTE modem
- DM320118 Microchip Trust Development Kit
- DT100104 ATECC608B Trust
- Accessories (USB cables, jumper connectors, etc.)
- (Optional) USB-to-Serial adapter

## Milestone 1 - Enable PPP-link with SIM7600EI on Raspberry Pi

### Step 1 - Installing PPP
To install PPP, open a terminal window and execute the below command.
```console
$ sudo apt install ppp
```

### Step 2 - Setting up provider
We will write our own provider that we will supply to the PPP daemon. Create a file named `my-provider` inside /etc/ppp/peers folder. You may need root privileges to do the steps - so we will first start a root shell.
```console
$ sudo su
$ vim /etc/ppp/peers/my-provider
```

The content of the `my-provider` should be as below.
```
# Replace with the port in your Raspberry Pi - can be ttyACMn as well
/dev/ttyUSBn

# Change this to a different rate if needed
921600

defaultroute

# Do not present a default IP address
noipdefault

# Use the DNS server as obtained by the modem

usepeerdns

# No authentication necessary
noauth

# Print debug messages wherever possible
debug

# This is is the chatscript that would be used - replace my-gprs with your own chatscript name
connect "/usr/sbin/chat -v -f /etc/chatscripts/my-gprs"
```

### Step 3 - Setting up chatscript
It is a good idea to place the chatscript inside `/etc/chatscripts/` folder. We will call our chatscript `my-chatscript`. Execute the below as root (continue the previous shell).
```console
$ vim /etc/chatscripts/my-chatscript
```

The content of `my-chatscript` should be as below.
```
ABORT	BUSY
ABORT	VOICE
ABORT	"NO CARRIER"
ABORT	"NO DIALTONE"
ABORT	"NO DIAL TONE"
ABORT	"NO ANSWER"
ABORT	"DELAYED"
ABORT	"ERROR"

# Abort if not attached to data network
ABORT	"+CGATT:0"

""	AT
OK	ATH
OK	ATE0

# Provide the pin for the SIM card (if any)
#OK	AT+CPIN=1234

# Enable full RF functionality - not necessary as by default RF is ON upon power-up
#OK	AT+CFUN=1

# Set up the PDP Context - very important step - replace the APN (Jionet)  with the one applicable to your network
OK	AT+CGDCONT=1,"IP","Jionet","",0,0
OK	ATD*99#
TIMEOUT	22
CONNECT	""
```
If your provider uses a different chatscript, create the new file with that name.

### Step 4 - Start a PPP connection
To start the PPP link, execute the below as root.
```console
$ pon my-provider
```
If all goes well, you should see PPP-related logs in your `dmesg` output.

Check that the `ppp0` interface is up using `ifconfig`.
```console
$ ifconfig ppp0
```

### Step 5 - Check that you have internet connectivity on ppp0 using ping
Verify internet connectivity by trying to ping google.com using the `ppp0` interface.

```console
$ ping google.com -I ppp0
```

### Step 6 - Exit root shell
We no more need the root shell - can choose to exit now.
```console
$ exit
```

## Milestone 2 - Build Microchip's cryptoauthlib on Raspberry Pi with PKCS11 support enabled

### Step 1 - Fetch cryptoauthlib from MicrochipTech github repo and checkout v3.3.3
Execute the below from a non-root shell at a location of your choice.
```console
$ git clone https://github.com/MicrochipTech/cryptoauthlib
$ cd cryptoauthlib
$ git checkout v3.3.3
```

### Step 2 - Create a directory to hold the cmake build outputs inside cryptoauthlib
Execute the below from a non-root shell while you are inside the cryptoauthlib folder.
```console
$ mkdir my-cal-build
$ cd my-cal-build
```

### Step 3 - Configure cmake build using cmake-gui
1. Open cmake-gui and provide the source code path as `path/to/cryptoauthlib` and build path as `path/to/cryptoauthlib/my-cal-build` directory.
2. Click on Configure button
3. There would be some default selections already - leave them untouched.
4. Select these options using the checkbox next to them: ATCA_HAL_I2C, ATCA_OPENSSL, ATCA_PKCS11, ATCA_TFLEX_SUPPORT, ATCA_TNGTLS_SUPPORT, ATCA_TNGLORA_SUPPORT, ATCA_TNG_LEGACY_SUPPORT, ATCA_USE_ATCAB_FUNCTIONS
5. Click on Configure button
6. Click on Generate button
7. Close cmake-gui

### Step 4 - Build and install cryptoauthlib
1. Execute make from within my-cal-build folder
```console
$ make
```
2. Install the library so that applications can use it
```console
$ sudo make install
```

### Step 5 - Set up PKCS11
Ensure that the packages mentioned in the  software setion above have been installed beforehand.

1. Obtain, configure, build and install libp11. NOTE: It is not necessary to do this from within cryptoauthlib - you can navigate to any other path as needed.
```console
$ git clone https://github.com/OpenSC/libp11.git
$ cd libp11
$ ./bootstrap
$ ./configure
$ make
$ sudo make install
```

### Step 6 - Create PKCS11 slot 0
When you installed cryptoauthlib, it created a template slot configuration at `/var/lib/cryptoauthlib`. Copy this template in the same folder as a file named `0.conf`.
```console
$ cp /var/lib/cryptoauthlib/slot.conf.tmpl /var/lib/cryptoauthlib/0.conf
```

Edit the `0.conf` as below.
1. Change the device to `ATECC608-TNGTLS` since we will be using the TNGTLS device on the DT100104.
2. Change the I2C address to `0x6A`
3. Change the interface type from `hid,i2c` to `i2c`
4. Set the I2C bus as `1` (the I2C exposed on RPi 40-pin connector is I2C1)

Overall, the interface entry should look like this.
```
interface = i2c,0x6A,1
```

### Step 7 - Test PKCS11 interface
1. Connect DT100104 to the I2C pins on Raspberry Pi 40-pin connector
2. On the command line, we will try to test the PKCS11 interface by listing all available objects.
```console
$ p11tool --provider /usr/lib/arm-linux-gnueabihf/libcryptoauth.so --list-all
```
You should see output something like below.
```
Object 0:
	URL: pkcs11:model=ATECC608A;manufacturer=Microchip%20Technology%20Inc;serial=231606F750596A01;token=00ABC;object=device;type=private
	Type: Private key (EC/ECDSA-SECP256R1)
	Label: device
	Flags: CKA_PRIVATE; CKA_SENSITIVE; 
	ID: 

Object 1:
	URL: pkcs11:model=ATECC608A;manufacturer=Microchip%20Technology%20Inc;serial=231606F750596A01;token=00ABC;object=device;type=public
	Type: Public key (EC/ECDSA-SECP256R1)
	Label: device
	ID: 

Object 2:
	URL: pkcs11:model=ATECC608A;manufacturer=Microchip%20Technology%20Inc;serial=231606F750596A01;token=00ABC;object=device;type=cert
	Type: X.509 Certificate (EC/ECDSA-SECP256R1)
	Expires: Fri Jan  1 04:53:23 2038
	Label: device
	ID: 

Object 3:
	URL: pkcs11:model=ATECC608A;manufacturer=Microchip%20Technology%20Inc;serial=231606F750596A01;token=00ABC;object=signer;type=cert
	Type: X.509 Certificate (EC/ECDSA-SECP256R1)
	Expires: Fri Jan  1 04:53:23 2038
	Label: signer
	Flags: CKA_CERTIFICATE_CATEGORY=CA; CKA_TRUSTED; 
	ID: 

```

## Milestone 3 - Enroll ATECC608-TNGTLS to AWS IoT cloud account

Please follow the instructions in Trust Platform Design Suite v2 (AWS - Trust&GO use-case for this process).

1. [Link to Trust Platform Design Suite v2](https://www.microchip.com/en-us/product/SW-TPDSV2)

2. [Link to webinar - AWS IoT with ATECC608 Trust&GO](https://www.microchip.com.hk/pub/web/Webinar%202%20-%20Pre-provisioned%20Secure%20Elements%20-%20Onboarding%20with%20Trust&GO%20for%20AWS%20IoT.mp4)


## Milestone 4 - Use AWS IoT SDK (Python) with PKCS11 support to perform pub-sub

### Step 1 - Get the AWS IoT Python SDK

Navigate into any preferred path on your system, clone the AWS IoT Python SDK and checkout tag v1.10.0.
```console
$ git clone https://github.com/aws/aws-iot-device-sdk-python-v2.git
$ cd aws-iot-device-sdk-python-v2
$ git checkout v1.10.0
```
### Step 2 - Install the AWS IoT Python SDK

If you prefer to work in a virtual environment, you can activate one now. Afte that, install the AWS IoT Python SDK by executing the below command. This command assumes python3 is the only `python` available on system. 
Use `python3` everywhere if `python2` and `python3` both exist.

```console
$ pip install awsiotsdk
```



