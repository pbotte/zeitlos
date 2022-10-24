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

</head>

<body>
    <table border="0" style="height: 100%; width: 100%; border-collapse: collapse;">
      <tbody>
        <tr>
          <td style="width: 10%; background-color: white; ">
            <p>&nbsp;</p>
          </td>
          <td style="width: 0%; height: 100%; text-align: center; background-color: white; vertical-align: center;" id="fullTable">
            <h1 align="center" id="mytext">...</h1>
          </td>
          <td style="width: 10%; background-color: white; ">
            <p>&nbsp;</p>
          </td>
        </tr>

      </tbody>
    </table>


    <script>
        var connected_flag = 0;
        var shop_status = 0; //client in shop
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

        setInterval(function () {
          switch (shop_status) {
            case 0:
              document.getElementById("mytext").innerHTML = "Initialisierung, bitte warten.";
              document.getElementById("fullTable").style.backgroundColor = "white";
              break;
            case 1:
              document.getElementById("mytext").innerHTML = "Laden ist frei.<br><br>Einkauf mit Kundenkarte/Girocard beginnen.";
              document.getElementById("fullTable").style.backgroundColor = "#44ff44";
              break;
            case 2:
              document.getElementById("mytext").innerHTML = "Authentifiziert.<br>Bitte Laden betreten.";
              document.getElementById("fullTable").style.backgroundColor = "#44ff44";
              break;
            case 3:
              document.getElementById("mytext").innerHTML = "Kunde kauft ein.<br>Bitte warten.";
              document.getElementById("fullTable").style.backgroundColor = "white";
              break;
            case 4:
              document.getElementById("mytext").innerHTML = "Kunde im Laden.<br>Einkauf beendet.";
              document.getElementById("fullTable").style.backgroundColor = "white";
              break;
            case 5:
              document.getElementById("mytext").innerHTML = "Bezahlung erfolgreich.";
              document.getElementById("fullTable").style.backgroundColor = "white";
              break;
            case 6:
              document.getElementById("mytext").innerHTML = "Kunde verlässt Laden";
              document.getElementById("fullTable").style.backgroundColor = "white";
              break;
            case 7:
              document.getElementById("mytext").innerHTML = "Vorbereitung für nächsten Kunden. Bitte warten.";
              document.getElementById("fullTable").style.backgroundColor = "white";
              break;
            case 8:
              document.getElementById("mytext").innerHTML = "Ein technischer Fehler ist aufgetreten.";
              document.getElementById("fullTable").style.backgroundColor = "#FF4444";
              break;
            case 9:
              document.getElementById("mytext").innerHTML = "Kunde benötigt Hilfe.";
              document.getElementById("fullTable").style.backgroundColor = "#FF4444";
              break;
            case 10:
              document.getElementById("mytext").innerHTML = "Laden geschlossen.";
              document.getElementById("fullTable").style.backgroundColor = "#FF4444";
              break;
            default:
              document.getElementById("mytext").innerHTML = "Technischer Fehler. <br><br>Unbekannter Zustand.";
              document.getElementById("fullTable").style.backgroundColor = "#FF4444";
              break;
          }

        }, 100);

    </script>

</body>

</html>
