<?php
$debugClientStrSuffix = "";
if (array_key_exists('debug', $_GET)) {
	$debugClientStrSuffix = 'debug';
}
?>
<html>
<style>

    /*
Prevent bluring of images = QR images
see: https://superuser.com/questions/530317/how-to-prevent-chrome-from-blurring-small-images-when-zoomed-in
*/
    img {
        image-rendering: optimizeSpeed;
        /*                     */
        image-rendering: -moz-crisp-edges;
        /* Firefox             */
        image-rendering: -o-crisp-edges;
        /* Opera               */
        image-rendering: -webkit-optimize-contrast;
        /* Chrome (and Safari) */
        image-rendering: pixelated;
        /* Chrome as of 2019   */
        image-rendering: optimize-contrast;
        /* CSS3 Proposed       */
        -ms-interpolation-mode: nearest-neighbor;
        /* IE8+                */
    }
    h1 {
        font-size: 100px;
    }
</style>

<head>
    <style>
        #overlay {
            position: fixed;
            display: none;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #CE1510;
            z-index: 2;
        }
        #text{
            position: absolute;
            top: 50%;
            left: 50%;
            font-size: 50px;
            color: white;
            transform: translate(-50%,-50%);
            -ms-transform: translate(-50%,-50%);
        }
    </style>
    <script>
    function mqtt_warning_on() {
        document.getElementById("overlay").style.display = "block";
    }
    function mqtt_warning_off() {
        document.getElementById("overlay").style.display = "none";
    }
    </script>
    <div id="overlay">
        <div id="text">Error:<br>no connection to MQTT server</div>
    </div>


    <title>Door Sign</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--For the plain library-->
    <!--<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.js" type="text/javascript"></script>-->
    <!--For the minified library: -->
    <!--<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js" type="text/javascript"></script>-->
    <script src="/mqttws31.min.js" type="text/javascript"></script>
    <script src='/forge-sha256/build/forge-sha256.min.js'></script>

    <script type="text/javascript">


        function onConnectionLost() {
            mqtt_warning_on();
            console.log("connection lost");
            connected_flag = 0;
        }
        function onFailure(message) {
            mqtt_warning_on();
            console.log("Failed");
            connected_flag = 0;
        }
        function onMessageArrived(r_message) {
            console.log("MQTT recv (" + r_message.destinationName + "): ", r_message.payloadString);

            if (r_message.destinationName == "homie/shopController/shopStatus") {
                shopStatus = parseInt(r_message.payloadString);
                console.log("new shopStatus", shopStatus);
            }
            if (r_message.destinationName == "homie/shopController/triggerHTMLPagesReload") {
                console.log("trigger page reload via MQTT");
                location.reload();
            }
        }

        function onConnected(recon, url) {
            mqtt_warning_off();
            console.log(" in onConnected " + reconn);
        }

        function onConnect() {
            mqtt_warning_off();
            console.log("Connected to " + host + ":" + port);
            connected_flag = 1
            console.log("connected_flag= ", connected_flag);
            mqtt.subscribe("homie/shopController/shopStatus");
            mqtt.subscribe("homie/shopController/triggerHTMLPagesReload");
            //message = new Paho.MQTT.Message("Hello World");
            //message.destinationName = "sensor1";
            //mqtt.send(message);
        }

        function MQTTconnect() {
            console.log("MQTT start connecting");
            var options = {
                timeout: 3,
                onSuccess: onConnect,
                onFailure: onFailure,
            };

            mqtt.connect(options);
            return false;
        }

    </script>

</head>

<body>
    <table border="0" style="height: 100%; width: 100%; border-collapse: collapse;">
        <tbody>
        <tr>
        <td style="width: 10%; background-color: white; ">
            <p>&nbsp;</p>
        </td>
        <td style="width: 80%; height: 40%; text-align: center; background-color: white; vertical-align: top;">
            <h1 align="center">Willkommen im Dorfladen</h1>
            <h1 align="center" id="mytext">...</h1>
        </td>
        <td style="width: 10%; background-color: white; ">
            <p>&nbsp;</p>
        </td>
        </tr>
        <tr>
            <td colspan="3" style="width: 100%; height: 15%; text-align: center; background-color: white; vertical-align: top;">
                <p>&nbsp;</p>
            </td>
            </tr>
        <tr>
        <td id="qrCodeArea" colspan="3" style="width: 100%; height: 45%; text-align: center; background-color: red; vertical-align: top;">
            <p align="center">
                <img src="/qr.php?" id="myImage" height="800" />
            </p>
            <p id="status">Connection Status: Not Connected</p>
        </td>
        </tr>
        </tbody>
    </table>


    <script>
        var connected_flag = 0;
        var shopStatus = 1; //client in shop
        var host = "192.168.10.28"; //shop-master
        var port = 8123;
        console.log("Set up the MQTT client to connect to " + host + ":" + port);
        var mqtt = new Paho.MQTT.Client(host, port, "clientdoor<?php echo "$debugClientStrSuffix";?>");
        mqtt.onConnectionLost = onConnectionLost;
        mqtt.onMessageArrived = onMessageArrived;
        mqtt.onConnected = onConnected;


        mqtt_warning_on();
        MQTTconnect();

        function UpdateQRCode() {
            var myImageElement = document.getElementById('myImage');
            var timestamp = Math.floor(Date.now() / 1000);

            var my_hash = forge_sha256('DasGeheimnis2020' + timestamp);

            myImageElement.src = 'http://' + host + '/qr.php?' +
                'text=' + encodeURIComponent('http://dorfladen.imsteinert.de/eingang/' +
                    '?hash=' + my_hash);
            console.log(myImageElement.src);
        }

        setInterval(function () { UpdateQRCode() }, 10 * 1000);
        setInterval(function () { if (connected_flag == 0) MQTTconnect() }, 5 * 1000);

        setInterval(function () { 
            if (shopStatus == 0) {
                //no client
                document.getElementById('myImage').style.display = "block";
                document.getElementById("mytext").innerHTML = "QR-Code scannen und eintreten!";
                document.getElementById("qrCodeArea").style.backgroundColor = "green";
            }
            if (shopStatus == 1) {
                //client in shop
                document.getElementById('myImage').style.display = "none";
                document.getElementById("mytext").innerHTML = "Bitte eintreten. Laden derzeit belegt.";
                document.getElementById("qrCodeArea").style.backgroundColor = "red";
            }

            }, 100);

        UpdateQRCode();
    </script>

</body>

</html>
