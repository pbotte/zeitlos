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

        function isEmpty(obj) {
            for(var prop in obj) {
                if(obj.hasOwnProperty(prop)) {
                    return false;
                }
            }
            return JSON.stringify(obj) === JSON.stringify({});
        }



	        function handleSelection(productid, value) {
	            console.log("Selected product:", productid, " value:", value);
    	            // Collecting form data
	            const formData = {
	                ProductID: productid,
	                NewCount: value
	            };
	            console.log("Form Data Submitted: ", formData); // Display the data in the console for verification
		    
		    // Converting formData object into a JSON string
    		    const formDataString = JSON.stringify(formData);
    
	    	  message = new Paho.MQTT.Message(formDataString);
		  message.destinationName = "homie/public_webpage_supplier/"+mqtt_user_name+"/cmd/basket/set_product_count";
		  console.log("Prepare Public Create Product Message: Set Product Count with parameter: "+formDataString)
		  mqtt.send(message);
		  console.log("Message successfully sent.")	
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
	    
	    if (r_message.destinationName == "homie/shop_controller/actualBasket") {
                var obj = JSON.parse(r_message.payloadString);
                //console.log(obj);
                var mstr = '';
                if (! isEmpty(obj['data'])) {
                    Object.values(obj['data']).forEach(element => {
                     mstr += '<tr><td style="width: 33%;">'+element['ProductName']+'</td>'+
                        '<td style="width: 10%; text-align: right; text-align: center;">'+element['withdrawal_units']+'</td> ';
			
			mstr += '<td style="width: 10%; text-align: right; text-align: center;"> '+
			'    <select id="numberSelect" name="numberSelect" onchange="handleSelection('+element['ProductID']+', this.value)"> ';
			for (let i = 0; i <= element['withdrawal_units']+1; i++) {
				temp_s = "";
				if (i == element['withdrawal_units']) temp_s = " selected ";
				mstr += '        <option value="'+i+'" '+temp_s+'>'+i+'</option> ';
				}
			mstr += '    </select></td>'+
                        '<td style="width: 34%; text-align: right;">'+element['price'].toLocaleString('de-DE', { 
  style                    : 'decimal', minimumFractionDigits    : 2, maximumFractionDigits    : 2})+'</td>'+
                        '</tr>\n';
                    }
                    );
                } else {
                    mstr += '<tr><td colspan="3">Noch keine Produkte entnommen.<br>&nbsp;<br>&nbsp;</td></tr>\n';
                }
                amountstr = obj['total'].toLocaleString('de-DE', {style: 'decimal', minimumFractionDigits    : 2, maximumFractionDigits    : 2})
                mstr += '<tr>'+
                    '<td style="width: 66%; vertical-align: bottom;" colspan="3"><strong>Summe:</strong></td>'+
                    '<td style="width: 34%; text-align: right; vertical-align: bottom;"><br /><br /><strong>'+ amountstr +'</strong></td>'+
                    '</tr>';
                document.getElementById("myBasketTable").innerHTML = mstr;

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
            mqtt.subscribe("homie/shop_controller/shop_overview/products");
            mqtt.subscribe("homie/shop_controller/actualBasket");
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
          18: "Einräumen durch Betreiber, Waage ausgewählt.",
          19: "Laden in technischer Wartung.",
          20: "Zuviel im Warenkorb."
        };


        mqtt_warning_on();
        MQTTconnect();


        setInterval(function () { if (connected_flag == 0) MQTTconnect() }, 5 * 1000);

        setInterval(function () {
          if (shop_status>=0 && shop_status<=20) {
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

            <h1>Hemmes24<br>Lieferanten-Zugang</h1>
            <p>Eingeloggt als: <?php echo $mqtt_user_name; ?></p>
	    
	    <form action="supplier_full.php" method="POST">
	        <input type="hidden" name="mqttusername" value="<?php echo $mqtt_user_name; ?>">
	        <input type="hidden" name="mqttpassword" value="<?php echo $mqtt_password; ?>">
	        Ladenverwaltung: <button type="submit">Ladenübersicht</button>
	    </form>


            <p id="mytext">...</p>
	    
	    
	    
	        <table border="1" style="border-collapse: collapse; width: 100%;" class="paleBlueRows">
    <thead>
    <tr>
    <td style="width: 33%; background-color: blue;"><span style="color: #ffffff;"><strong>Produkt</strong></span></td>
    <td style="width: 10%; background-color: blue; text-align: center;"><span style="color: #ffffff;""><strong>Menge</strong></span></td>
    <td style="width: 23%; background-color: blue; text-align: center;"><span style="color: #ffffff;""><strong>Korrektur</strong></span></td>
    <td style="width: 34%; background-color: blue; text-align: right;"><span style="color: #ffffff;"><strong>Preis in &euro;</strong></span></td>
    </tr>
    </thead>
    <tbody id="myBasketTable">
    </tbody>
    </table>

	<p>&nbsp;</p>
	<h3>Neues Produkt in den Warenkorb legen</h3>
	<script>
        function handleSubmit() {
            const dropdown = document.getElementById('numberDropdown');
            const selectedValue = dropdown.value;
            alert('Sie haben die Nummer ' + selectedValue + ' ausgewählt.');
	    handleSelection(selectedValue, 1);
        }
    </script>
	<form onsubmit="handleSubmit(); return false;">
        <label for="numberDropdown">Wählen Sie eine Nummer:</label>
        <select id="numberDropdown" name="numberDropdown">
            <!-- Dropdown-Optionen werden hier dynamisch generiert -->
            <script>
                for (let i = 1; i <= 300; i++) {
                    document.write('<option value="' + i + '">' + i + '</option>');
                }
            </script>
        </select>
        <button type="submit">1x in den Warenkorb</button>
    </form>
    
    

</body>

</html>
