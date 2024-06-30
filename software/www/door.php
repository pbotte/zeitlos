<?php
$debugClientStrSuffix = "";
if (array_key_exists('debug', $_GET)) {
	$debugClientStrSuffix = 'debug';
}

?>
<?php
/*
GENERATE Codes and CRC in Python

import base64
import gzip
import zlib

data_str = "hallo"

compressed_data = zlib.compress(data_str.encode(), level=9, wbits=15)
encoded_data = base64.urlsafe_b64encode(compressed_data).rstrip(b'=').decode()

s = ":".join("{:02x}".format(c) for c in compressed_data)
print(s)

translation_table = str.maketrans('+/', '-_')
encoded_data = encoded_data.translate(translation_table)

print(encoded_data)
*/
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
        font-family: Verdana, Arial, Helvetica, sans-serif;
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
    <!--Show the following sign until a MQTT connection is establised-->
    <div id="overlay" style="display:block">
        <div id="text">Error:<br>no connection to MQTT server</div>
    </div>


    <title>Door Sign</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--For the plain library-->
    <!--<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.js" type="text/javascript"></script>-->
    <!--For the minified library: -->
    <!--<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js" type="text/javascript"></script>-->
    <script src="/mqttws31.min.js" type="text/javascript"></script>

    <script src="pako/dist/pako.min.js"></script>
    
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

            if (r_message.destinationName == "homie/shop_controller/shop_status") {
                shop_status = parseInt(r_message.payloadString);
                console.log("new shop_status", shop_status);
            }
            if (r_message.destinationName == "homie/shop_controller/triggerHTMLPagesReload") {
                console.log("trigger page reload via MQTT");
                location.reload();
            }
            if (r_message.destinationName == "homie/shop_controller/invoice_json") {
                invoice_json = r_message.payloadString;
                console.log("new invoice_json", invoice_json);
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
            mqtt.subscribe("homie/shop_controller/shop_status");
            mqtt.subscribe("homie/shop_controller/invoice_json");
            mqtt.subscribe("homie/shop_controller/triggerHTMLPagesReload");
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

    <script>
		//From https://stackoverflow.com/questions/18638900/javascript-crc32
		var makeCRCTable = function(){
            var c;
            var crcTable = [];
            for(var n =0; n < 256; n++){
                c = n;
                for(var k =0; k < 8; k++){
                    c = ((c&1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1));
                }
                crcTable[n] = c;
            }
            return crcTable;
        }

        var crc32 = function(str) {
            var crcTable = window.crcTable || (window.crcTable = makeCRCTable());
            var crc = 0 ^ (-1);

            for (var i = 0; i < str.length; i++ ) {
                crc = (crc >>> 8) ^ crcTable[(crc ^ str.charCodeAt(i)) & 0xFF];
            }

            return (crc ^ (-1)) >>> 0;
        };
	</script>

</head>

<body>
    <table border="0" style="height: 100%; width: 100%; border-collapse: collapse;">
      <tbody>
        <tr>
          <td style="width: 100%; height: 100%; text-align: center; background-color: white; vertical-align: center;" id="fullTable">
            <div align="center" id="mytext">Verbinden...</div>
          </td>
        </tr>

      </tbody>
    </table>

    <script>
    function encodeDataString(data_str) {
        var c1 = pako.deflate(data_str, { level: 9 , windowBits:15});

        var base64EncodedData = btoa(String.fromCharCode.apply(null, c1))
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=+$/, '');

        //document.write(base64EncodedData);

        var SECRETSTR= "blablablaskfjshfushdfisuh5487wzfisaubsidab";
        var str_to_check = SECRETSTR + base64EncodedData;
        var correct_check_str = crc32(str_to_check).toString(16);
        correct_check_str = correct_check_str.padStart(8, "0"); //put leading "0" if too short
        //document.write("\n"+correct_check_str.toString(16));


        const iframe = document.getElementById('myIframe');
        console.log('/invoice.php?d='+base64EncodedData+'&c='+correct_check_str+'&out=html');
        iframe.src = '/invoice.php?d='+base64EncodedData+'&c='+correct_check_str+'&out=html';

        const qrpic = document.getElementById('qrpic');
        qrpic.src="/qr.php?t=https://www.hemmes24.de/code/invoice.php?d%3D"+base64EncodedData+"%26c%3D"+correct_check_str;
    }
    </script>

    <script>
        var statusData = [
            { message: "Initialisierung, bitte warten.", backgroundColor: "white" },
            { message: "Laden ist frei.<br><br><font size=\"50\">Halten Sie Ihre Girocard, Kreditkarte oder Handy mit aktivierter Bezahlfunktion vor das Kartenlesegerät rechts der Türe.</font>", backgroundColor: "#44ff44" },
            { message: "Bitte warten.<br>Laden wird vorbereitet.", backgroundColor: "#44ff44" },
            { message: "Laden wird gerade betreten / verlassen.<br>Bitte warten.", backgroundColor: "white" },
            { message: "Überprüfung, ob Laden belegt.<br>Bitte warten..", backgroundColor: "white" },
            { message: `<table border="0" style="height: 1020; width: 100%; border-collapse: collapse;">
        <tr>
          <td style="width: 30%; height: 100%; text-align: center; background-color: white; vertical-align: center;" id="fullTable">
            <div align="center">
              <p><font size=\"30\">Kassenbon</font></p>
              <p><img id="qrpic"></p>
              <p><font size=\"20\">Anzeige für 60 Sekunden.</font></p>
            </div>
            <div align="center" id="mytext"></div>
          </td>
          <td style="width: 70%; height: 100%; text-align: center; background-color: white; vertical-align: top;" id="fullTable">
            <div align="center">
              <iframe id="myIframe" width="600" height="1100" style="transform-origin: top left;transform: scale(0.9,0.9);-webkit-transform: scale(0.9,0.9);-moz-transform: scale(0.9,0.9);" frameBorder="0"></iframe>
            </div>
          </td>
        </tr>
    </table>`, backgroundColor: "white" },
            { message: "Laden geschlossen. Neue Produkte werden gerade eingelegt.", backgroundColor: "#FF4444" },
            { message: "Vorbereitung. Bitte warten.", backgroundColor: "white" },
            { message: "Ein technischer Fehler ist aufgetreten.", backgroundColor: "#FF4444" },
            { message: "Kunde benötigt Hilfe.", backgroundColor: "#FF4444" },
            { message: "Laden geschlossen.", backgroundColor: "#FF4444" },
            { message: "Überprüfung, ob Laden belegt.<br>Bitte warten.", backgroundColor: "white" },
            { message: "Laden belegt.<br>Bitte warten.", backgroundColor: "white" },
            { message: "Fehler beim Kartenterminal.", backgroundColor: "#FF4444" },
            { message: "Bitte den Laden betreten", backgroundColor: "#44ff44" },
            { message: "Abrechnung wird vorbereitet.", backgroundColor: "white" },
            { message: "Kartenterminal: Zeit abgelaufen.", backgroundColor: "white" }, 
            { message: "Warten auf Kartenterminal.", backgroundColor: "white" },
            { message: "Laden geschlossen. Neue Produkte werden gerade eingelegt.", backgroundColor: "#FF4444" },
            { message: "Laden geschlossen. Technische Wartung.", backgroundColor: "#FF4444" },
            { message: "Laden belegt.<br>Bitte warten.", backgroundColor: "#FF4444" }
        ];

        var connected_flag = 0;
        var shop_status = 0; //client in shop
        var invoice_json = ""; 
        var host = "192.168.10.10"; //shop-master
        var port = 9001;
        console.log("Set up the MQTT client to connect to " + host + ":" + port);
        var mqtt = new Paho.MQTT.Client(host, port, "clientdoor<?php echo "$debugClientStrSuffix";?>");
        mqtt.onConnectionLost = onConnectionLost;
        mqtt.onMessageArrived = onMessageArrived;
        mqtt.onConnected = onConnected;


        mqtt_warning_on();
        MQTTconnect();


        setInterval(function () { if (connected_flag == 0) MQTTconnect() }, 5 * 1000);

        var last_shop_status = -1;
        setInterval(function () {
            if (last_shop_status != shop_status) { //nur, wenn sich der Zustand geändert hat.
                if ((shop_status >= 0) && (shop_status < statusData.length)) {
                    if (shop_status == 5) { //Kassenbonanzeige
                        document.getElementById("mytext").innerHTML = statusData[shop_status].message;
                        encodeDataString(invoice_json);
                    } else {
                        document.getElementById("mytext").innerHTML = '<h1 align="center">'+statusData[shop_status].message+'</h1>';
                    }
                    document.getElementById("fullTable").style.backgroundColor = statusData[shop_status].backgroundColor;
                } else {
                    // Wenn shop_status außerhalb des gültigen Bereichs liegt
                    document.getElementById("mytext").innerHTML = "Ungültiger Zustand.";
                    document.getElementById("fullTable").style.backgroundColor = "red";
                }

                last_shop_status = shop_status;
            }
         }, 500);

    </script>

</body>

</html>
