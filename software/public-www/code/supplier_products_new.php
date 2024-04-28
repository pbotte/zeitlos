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
    
    <script type="text/javascript" src="https://code.jquery.com/jquery-3.7.1.js"></script>
    <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.2/moment.min.js"></script>
    

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


        mqtt_warning_on();
        MQTTconnect();


        setInterval(function () { if (connected_flag == 0) MQTTconnect() }, 5 * 1000);

    </script>
    

            <h1>Hemmes24 Produktübersicht</h1>
            <p>Eingeloggt als: <?php echo $mqtt_user_name; ?></p>
	    <form action="supplier_full.php" method="POST">
	        <input type="hidden" name="mqttusername" value="<?php echo $mqtt_user_name; ?>">
	        <input type="hidden" name="mqttpassword" value="<?php echo $mqtt_password; ?>">
	        Ladenverwaltung: <button type="submit">Ladenübersicht</button>
	    </form>
	    <form action="supplier_products.php" method="POST">
	        <input type="hidden" name="mqttusername" value="<?php echo $mqtt_user_name; ?>">
	        <input type="hidden" name="mqttpassword" value="<?php echo $mqtt_password; ?>">
	        Ladenverwaltung: <button type="submit">Produktverwaltung</button>
	    </form>
	
	
	<script>
	        function handleCreateNewProduct(event) {
	            event.preventDefault(); // Prevent the form from submitting in the traditional way

	            // Collecting form data
	            const formData = {
	                Supplier: document.getElementById('supplier').value,
	                ProductName: document.getElementById('productName').value,
	                ProductDescription: document.getElementById('productDescription').value,
	                PricePerUnit: document.getElementById('pricePerUnit').value,
	                kgPerUnit: document.getElementById('kgPerUnit').value,
	                VAT: document.getElementById('vat').value
	            };

	            console.log("Form Data Submitted: ", formData); // Display the data in the console for verification
		    
		    // Converting formData object into a JSON string
    		    const formDataString = JSON.stringify(formData);
    
	    	  message = new Paho.MQTT.Message(formDataString);
		  message.destinationName = "homie/public_webpage_supplier/"+mqtt_user_name+"/cmd/create_product";
		  console.log("Prepare Public Create Product Message from Supplier: handleCreateNewProduct with parameter: "+formDataString)
		  mqtt.send(message);
		  console.log("Message successfully sent.")	
		  window.alert("Produkt wurde angelegt.");	    
	        }
				
	</script>
	
	
	<h1>Neues Produkt anlegen</h1>
	    <form onsubmit="handleCreateNewProduct(event)">
	        <label for="supplier">Lieferant:</label>
	        <input type="text" id="supplier" name="supplier" required><br><br>

	        <label for="productName">Produktname:</label>
	        <input type="text" id="productName" name="productName" required><br><br>

	        <label for="productDescription">Beschreibung:</label>
	        <textarea id="productDescription" name="productDescription" cols="30" rows="5"></textarea><br><br>

	        <label for="pricePerUnit">Einheitspreis in €:</label>
	        <input type="number" step="0.01" id="pricePerUnit" name="pricePerUnit" required value="1.00"><br><br>

	        <label for="kgPerUnit">Masse in kg pro Einheit:</label>
	        <input type="number" step="0.001" id="kgPerUnit" name="kgPerUnit" required value="0.500"><br><br>

	        <label for="vat">MWSt.:</label>
	        <select id="vat" name="vat" required>
	            <option value="0">0%</option>
	            <option value="0.07" selected>7%</option>
	            <option value="0.19">19%</option>
	        </select><br><br>
		
	        <button type="submit">Eintragen</button>
	    </form>
	    
        
    
</body>

</html>
