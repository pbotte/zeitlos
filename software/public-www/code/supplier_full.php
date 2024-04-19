<?php
$mqtt_user_name = "Gude";
if (array_key_exists('mqttusername', $_POST)) {
	$mqtt_user_name = $_POST['mqttusername'];
}
$mqtt_password = "Gude";
if (array_key_exists('mqttpassword', $_POST)) {
	$mqtt_password = $_POST['mqttpassword'];
}
?>
<html>
<script>
var mqtt_user_name = '<?php echo $mqtt_user_name; ?>';
var mqtt_password = '<?php echo $mqtt_password; ?>';
</script>
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
        font-size: 30;
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
        <div id="text">Fehler: Keine Verbindung zum MQTT-Server.<br><br>Stimmen die <a href="supplier_full_landing.php">Benutzerdaten</a>?</div>
    </div>


    <title>Lieferant Zugang</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--For the plain library-->
    <!--<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.js" type="text/javascript"></script>-->
    <!--For the minified library: -->
    <!--<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js" type="text/javascript"></script>-->
    <script src="mqttws31.min.js" type="text/javascript"></script>
    <script src="mqtt_broker_cred_full.js" type="text/javascript"></script>

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
            var options = {
                timeout: 3,
                onSuccess: onConnect,
                onFailure: onFailure,
		userName : mqtt_user_name,
		password : mqtt_password,
		useSSL: true
            };
            console.log("MQTT start connecting with these options:");
	    console.log(options);

            mqtt.connect(options);
            return false;
        }


	function sendMQTTMessage() {
	  message = new Paho.MQTT.Message("0");
	  message.destinationName = "homie/public_webpage_supplier/"+mqtt_user_name+"/cmd/open_door";
	  console.log("Prepare Public Submit Message from Supplier")
	  mqtt.send(message);
	  console.log("Message successfully sent.")
	}
    </script>

</head>

<body>

    <script>
        var connected_flag = 0;
        var shop_status = 0; //client in shop
        console.log("Set up the MQTT client to connect to " + host + ":" + port);
        var mqtt = new Paho.MQTT.Client(host, port, "public_webpage_viewer_"+location.hostname+"_"+Math.floor(Math.random() * 100000));
        mqtt.onConnectionLost = onConnectionLost;
        mqtt.onMessageArrived = onMessageArrived;
        mqtt.onConnected = onConnected;


        var shop_status_descr = {
          0: "Geräte Initialisierung", 
          1: "Bereit, Kein Kunde im Laden", 
          2: "Kunde authentifiziert/Waagen tara",
          3: "Kunde betritt/verlässt gerade den Laden", 
          4: "Möglicherweise: Einkauf finalisiert & Kunde nicht mehr im Laden",
          5: "Einkauf beendet und abgerechnet", 
          6: "Einräumen durch Betreiber",
          7: "Warten auf: Vorbereitung für nächsten Kunden", 
          8: "Technischer Fehler aufgetreten", 
          9: "Kunde benötigt Hilfe",
          10: "Laden geschlossen", 
          11: "Kunde möglicherweise im Laden", 
          12: "Kunde sicher im Laden", 
          13: "Fehler bei Authentifizierung",
          14: "Bitte Laden betreten", 
          15: "Kunde nicht mehr im Laden. Abrechnung wird vorbereitet.",
          16: "Timeout Kartenterminal",
          17: "Warten auf: Kartenterminal Buchung erfolgreich",
          18: "Einräumen durch Betreiber, Waage ausgewählt."
        };


        mqtt_warning_on();
        MQTTconnect();


        setInterval(function () { if (connected_flag == 0) MQTTconnect() }, 5 * 1000);

        setInterval(function () {
          if (shop_status>=0 && shop_status<=16) {
            document.getElementById("mytext").innerHTML = "Aktuell: "+shop_status_descr[shop_status];
          } else {
            document.getElementById("mytext").innerHTML = "Technischer Fehler. <br><br>Unbekannter Zustand.";
          }

        }, 100);

    </script>


    <style>
      .block_green {
        display: block;
        width: 100%;
        border: none;
        background-color: #04AA6D;
        padding: 14px 28px;
        font-size: 20px;
        cursor: pointer;
        text-align: center;
    }
      .block_red {
        display: block;
        width: 100%;
        border: none;
        background-color: #CE1510;
        padding: 14px 28px;
        font-size: 20px;
        cursor: pointer;
        text-align: center;
    }
    </style>

    <table border="0" style="height: 100%; width: 100%; border-collapse: collapse;">
      <tbody>
        <tr>
          <td style="width: 10%; background-color: white; ">
            <p>&nbsp;</p>
          </td>
          <td style="width: 0%; height: 100%; text-align: center; background-color: white; vertical-align: center;" id="fullTable">
            <h1>Hemmes24<br>Lieferanten-Zugang</h1>
            <p>Eingeloggt als: <?php echo $mqtt_user_name; ?></p>
            <p id="mytext">...</p>
            <p>
              <button type="button" class="block_green" onClick="sendMQTTMessage();">Türe öffnen</button>
            </p>
          </td>
          <td style="width: 10%; background-color: white; ">
            <p>&nbsp;</p>
          </td>
        </tr>

      </tbody>
    </table>

</body>

</html>
