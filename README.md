# Kickstart Embedded - Parry Tech SIM7600EI RPi Hat Evaluation

**!!! THIS IS A WORK-IN-PROGRESS !!!**

## Objectives


1. To achieve AWS-IoT MQTT communication using Microchip ATECC608-TNGTLS as the identity provider to the AWS IoT cloud
2. The connection to cloud is done using Parry Tech's SIM7600EI based Raspberry Pi hat

## Major milestones

1. &#9989; Enable PPP-link with SIM7600EI on Raspberry Pi
2. &#9989; Build and test Microchip's cryptoauthlib on Raspberry Pi with PKCS11 support enabled
3. &#9989; Enroll ATECC608-TNGTLS to AWS IoT cloud account
4. &#9989; Use AWS IoT SDK (C or Python) with PKCS11 support to perform pub-sub
5. &#10060; Achieve two-way communication between Raspberry Pi and AWS dashboard/GUI/CLI with node

##  Software 
- Raspberry Pi Buster (32-bit)
- [Microchip Cryptoauthlib](https://github.com/MicrochipTech/cryptoauthlib)
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
```
$ sudo apt install ppp
```

### Step 2 - Setting up provider
We will write our own provider that we will supply to the PPP daemon. Create a file named `my-provider` inside /etc/ppp/peers folder. You may need root privileges to do the steps - so we will first start a root shell.
```
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
```
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
```
$ pon my-provider
```
If all goes well, you should see PPP-related logs in your `dmesg` output.

Check that the `ppp0` interface is up using `ifconfig`.
```
$ ifconfig ppp0
```

### Step 5 - Check that you have internet connectivity on ppp0 using ping
Verify internet connectivity by trying to ping google.com using the `ppp0` interface.

```
$ ping google.com -I ppp0
```

### Step 6 - Exit root shell
We no more need the root shell - can choose to exit now.
```
$ exit
```

## Milestone 2 - Build Microchip's cryptoauthlib on Raspberry Pi with PKCS11 support enabled

### Step 1 - Fetch cryptoauthlib from MicrochipTech github repo and checkout v3.3.3
Execute the below from a non-root shell at a location of your choice.
```
$ git clone https://github.com/MicrochipTech/cryptoauthlib
$ cd cryptoauthlib
```

### Step 2 - Create a directory to hold the cmake build outputs inside cryptoauthlib
Execute the below from a non-root shell while you are inside the cryptoauthlib folder.
```
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
```
$ make
```
2. Install the library so that applications can use it
```
$ sudo make install
```

### Step 5 - Set up PKCS11
Ensure that the packages mentioned in the  software setion above have been installed beforehand.

1. Obtain, configure, build and install libp11. NOTE: It is not necessary to do this from within cryptoauthlib - you can navigate to any other path as needed.
```
$ git clone https://github.com/OpenSC/libp11.git
$ cd libp11
$ ./bootstrap
$ ./configure
$ make
$ sudo make install
```

### Step 6 - Create PKCS11 slot 0
When you installed cryptoauthlib, it created a template slot configuration at `/var/lib/cryptoauthlib`. Copy this template in the same folder as a file named `0.conf`.
```
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
```
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
```
$ git clone https://github.com/aws/aws-iot-device-sdk-python-v2.git
$ cd aws-iot-device-sdk-python-v2
```
### Step 2 - Install the AWS IoT Python SDK

- It is recommended to use a virtual environment for your development unless you are confident that installing new packages in not going to break any existing feature.
- Using Python3 is preferred. This procedure has been tested with Python3 only.

To set up and activate a virtual environment, navigate to the directory where you want the virtual environment to reside and execute the below.
```
$ python3 -m venv vpython3
$ . vpython3/bin/activate
(vpython3) $
```
You should now see your bash prompt preceded by the name of your virtual environment surrounded by parantheses.

To install the AWS IoT Python SDK, execute the below command.
```
(vpython3) $ python3 -m pip install path/to/the/aws-iot-device-sdk-python-v2/repo
```

To check that the installation was successful, run a `pip freeze` to see what modules the python environment has. 
```
(vpython3) $ pip freeze
```

### Step 3 - Set up a test thing using ATECC608-TNGTLS

**You can choose to skip this step if you already have an AWS IoT thing whose credentials are inside the ATECC608-TNGTLS chip.** 

We will now create an AWS IoT thing that we will then use for our future steps. AWS IoT Core makes it very easy to create a thing using its dashboard. Please follow the below steps. 

- Log into your AWS account and select the `AWS IoT Core` service.
- Click on `Manage` and then `Things`
- Click on `Create Things` button
- Select `Create Single Thing` and click `Next`
- Enter Thing name as `my_rpi_test_thing`. We don't need to configure any other optional feature as of now. Click `Next`.
- Click on `Upload CSR`. We will now generate a CSR or Certificate Signing Request using our ATECC608-TNGTLS.
- Connect the ATECC608-TNGTLS to the Raspberry Pi and execute the below command to generate the CSR. The below command will generate a CSR name `my_rpi_test_thing_csr.csr` in the `/home/pi` folder.
```
(vpython3) $ openssl req -engine pkcs11 -key "pkcs11:token=00ABC;object=device;type=private" -keyform engine -new -out my_rpi_test_thing.csr -subj "/CN=MY RPI TEST THING"
```
- Go back to the AWS IoT Core portal and click on `Choose File` and select the newly created `my_rpi_test_thing_csr.csr` file.
- Select an existing policy if you have that allows an IoT Device to connect to your AWS IoT Core account. If you don't have one, create one now using [this documentation](https://docs.aws.amazon.com/iot/latest/developerguide/example-iot-policies.html). Once done, click `Create Thing`.

Once the thing is created, you can select it, navigate to the `Certificates` tab and download the certificate associated with your thing and rename it to `my_rpi_test_thing_crt.crt`.

We shall use this during our next steps.

### Step 4 - Test the PKCS11 sample application

We are now ready to try out the sample application provided in the SDK. This application simply tries to connect to your AWS endpoint using the private key from the ATECC608-TNGTLS and the certificate provided to the application as an argument. If you followed step 3, then this certificate is the `rpi_test_thing_crt.crt` file.

Navigate into the samples directory of the AWS IoT Python SDK and execute the below command. Remember to do this in an activated virtual environment.
```
(vpython3) $ python3 pkcs11_connect.py --endpoint a************-ats.iot.us-west-2.amazonaws.com --cert ~/my_rpi_test_thing_crt.crt --pkcs11_lib /usr/lib/libcryptoauth.so --token_label 00ABC --key_label device --pin 1234 --client_id my_rpi_test_thing --port 8883 --ca_file ~/AmazonRootCA1.pem --verbosity NoLogs
```
In the above command
- Provide your own AWS endpoint - this can be obtained from the thing details on the AWS IoT Core dashboard
- Provide a CA file in case you get a connection error. The `AmazonRootCA1.pem` can be obtained from [here](https://www.amazontrust.com/repository/AmazonRootCA1.pem).

If all goes well, you should see a log as below.
```
Loading PKCS#11 library '/usr/lib/libcryptoauth.so' ...
Loaded!
Connecting to avu39804vjdlk-ats.iot.us-west-2.amazonaws.com with client ID 'my_rpi_test_thing'...
Connected!
Disconnecting...
Disconnected!
```

**PRO-TIP: You can verify that the connection was done successfully by going back to your AWS IoT Core dashboard and then going to the Monitor page. Refresh the page after a couple of minutes, and you should see that a successful connection was done recently.**

Give yourself a pat on the back - you have successfully performed your first successful mutual TLS authentication to AWS IoT Core using ATECC608-TNGTLS!

### Step 5 - Let us do some Publish-Subscribe using our PKCS#11 based thing

- Copy the `pkcs11_pubsub.py` from this repository into the `samples` folder of the `aws-iot-device-sdk-python-v2` repository
- In the AWS IoT Core dashboard, open an MQTT client by clicking on `Test` and then `MQTT test client`
- Assuming that the Raspberry Pi will publish to a topic called `$aws/things/<client id>/shadow/rpi_publish` and will subscribe to a topic called `$aws/things/<client id>/shadow/rpi_subscribe`, we will subscribe and publish to these topics respectively from the MQTT test client
- Navigate to the samples directory and execute the below command - ensure that the virtual environment we created before is activated beforehand.
```
(vpython3) $ python3 pkcs11_pubsub.py --endpoint a************-ats.iot.us-west-2.amazonaws.com --cert ~/my_rpi_test_thing_crt.crt --pkcs11_lib /usr/lib/libcryptoauth.so --token_label 00ABC --key_label device --pin 1234 --client_id my_rpi_test_thing --port 8883 --client_id my_rpi_test_thing --ca_file ~/AmazonRootCA1.pem --verbosity NoLogs --pub_topic rpi_publish --payload "My Message" --num_pub 10 --sub_topic rpi_subscribe --delay_secs 1
```

If all goes well, you should see logs similar to the below.
```
Loading PKCS#11 library '/usr/lib/libcryptoauth.so' ...
Loaded!
Connecting to a************-ats.iot.us-west-2.amazonaws.com with client ID 'my_rpi_test_thing'...
Connected!
Subscribing to topic '$aws/things/my_rpi_test_thing/shadow/rpi_subscribe'...
Subscribed with QoS.AT_LEAST_ONCE
Publishing to topic $aws/things/my_rpi_test_thing/shadow/rpi_publish...
Publishing to topic $aws/things/my_rpi_test_thing/shadow/rpi_publish...
Publishing to topic $aws/things/my_rpi_test_thing/shadow/rpi_publish...
Publishing to topic $aws/things/my_rpi_test_thing/shadow/rpi_publish...
Publishing to topic $aws/things/my_rpi_test_thing/shadow/rpi_publish...
Publishing to topic $aws/things/my_rpi_test_thing/shadow/rpi_publish...
Publishing to topic $aws/things/my_rpi_test_thing/shadow/rpi_publish...
Publishing to topic $aws/things/my_rpi_test_thing/shadow/rpi_publish...
Publishing to topic $aws/things/my_rpi_test_thing/shadow/rpi_publish...
Publishing to topic $aws/things/my_rpi_test_thing/shadow/rpi_publish...
Disconnecting...
Disconnected!
```
- Next time you run this application, you can try to publish from the MQTT test client to the topic `$aws/things/my_rpi_test_thing/shadow/rpi_subscribe` and observe the console prints showing the messages you published.