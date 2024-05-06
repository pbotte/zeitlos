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
    
    <!-- CSS for the dialog box -->
    <style>
	    #productDialog {
	    position: fixed;
	    left: 0;
	    top: 0;
	    width: 100%;
	    height: 100%;
	    background: rgba(0, 0, 0, 0.8);
	    display: flex;
	    align-items: center;
	    justify-content: center;
	}

	#dialogContent {
	    background: white;
	    padding: 20px;
	    border-radius: 5px;
	    width: 300px;
	    max-height: 80vh;
	    overflow-y: auto;
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
    
    <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/2.0.3/css/dataTables.dataTables.css">
    <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/datetime/1.5.2/css/dataTables.dateTime.min.css">
    <script type="text/javascript" src="https://code.jquery.com/jquery-3.7.1.js"></script>
    <script type="text/javascript" src="https://cdn.datatables.net/2.0.3/js/dataTables.js"></script>
    <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.2/moment.min.js"></script>
    <script type="text/javascript" src="https://cdn.datatables.net/datetime/1.5.2/js/dataTables.dateTime.min.js"></script>


    <script type="text/javascript">
    
    	function updateTableWithJsonData(jsonData) {
	    const tableBody = document.getElementById('productsTable').getElementsByTagName('tbody')[0];
    
	    Object.values(jsonData).forEach(product => {
	        const row = document.createElement('tr');
        
	        row.innerHTML = `
	            <td>${product.ProductName}</td>
	            <td>${product.ProductDescription || ''}</td>
	            <td>${product.PricePerUnit.toFixed(2)}</td>
	            <td>${product.kgPerUnit.toFixed(3)}</td>
	            <td>${product.VAT}</td>
	            <td>${product.Supplier}</td>
	        `;
       		row.addEventListener('click', () => {
            showProductDetails(product);
            document.getElementById('deleteButton').addEventListener('click', confirmDelete);
        });
        
	        tableBody.appendChild(row); 
	    } );
	}
    
	// Function to parse JSON string and populate dropdown
	function populateTableFromJsonString(jsonString) {
	    // Parse the JSON string into an object
	    const data = JSON.parse(jsonString);

	    // Convert the object to an array and sort it based on ProductName
	    const sortedData = Object.values(data).sort((a, b) => {
	        const nameA = a.Supplier.toUpperCase()+' '+a.ProductName.toUpperCase(); // ignore upper and lowercase
	        const nameB = b.Supplier.toUpperCase()+' '+b.ProductName.toUpperCase(); // ignore upper and lowercase
	        if (nameA < nameB) {
	            return -1;
	        }
	        if (nameA > nameB) {
	            return 1;
	        }
	        return 0;
	    });
	    
	    updateTableWithJsonData(data);
	    
	    new DataTable('#productsTable');

	}    
    


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
	    
            if (r_message.destinationName == "homie/shop_controller/shop_overview/products") {
//                console.log("Products: ");
//		console.log(r_message.payloadString);
		populateTableFromJsonString(r_message.payloadString);
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
          19: "Laden in technischer Wartung."
        };


        mqtt_warning_on();
        MQTTconnect();


        setInterval(function () { if (connected_flag == 0) MQTTconnect() }, 5 * 1000);

        setInterval(function () {
          if (shop_status>=0 && shop_status<=19) {
            document.getElementById("mytext").innerHTML = "Aktuell: "+shop_status_descr[shop_status];
          } else {
            document.getElementById("mytext").innerHTML = "Technischer Fehler. <br><br>Unbekannter Zustand.";
          }

        }, 100);

    </script>
    
    <script>
    function showProductDetails(product) {
	    const dialog = document.getElementById('productDialog');
	    const content = document.getElementById('dialogContent');

            // ${product.ProductID}
	    content.innerHTML = `
	        <p>Hinweis: Bearbeitung von bestehenden Produkten noch nicht möglich.</p>

	        <input type="hidden" id="productID" name="productID" value="${product.ProductID}">

	        <label for="productName">Produktname:</label>
	        <input type="text" id="productName" name="productName" value="${product.ProductName}"><br>

	        <label for="description">Beschreibung:</label>
	        <textarea type="text" id="description" name="description" rows="5" cols="20">${product.ProductDescription || ''}</textarea><br>

	        <label for="priceType">Preistyp:</label>
	        <input type="number" id="priceType" name="priceType" value="${product.PriceType}"><br>

	        <label for="pricePerUnit">Einheitspreis in €:</label>
	        <input type="number" step="0.01"  id="pricePerUnit" name="pricePerUnit" value="${product.PricePerUnit.toFixed(2)}"><br>

	        <label for="kgPerUnit">Masse in kg pro Einheit:</label>
	        <input type="number" step="0.001" id="kgPerUnit" name="kgPerUnit" value="${product.kgPerUnit.toFixed(3)}"><br>

	        <label for="vat">MWSt.:</label>
	        <input type="number" step="0.01" id="vat" name="vat" value="${product.VAT}"><br>

	        <label for="supplier">Lieferant:</label>
	        <input type="text" id="supplier" name="supplier" value="${product.Supplier}"><br>

	    `;
	    const deleteButton = document.getElementById('deleteButton');
		deleteButton.setAttribute('data-product-id', product.ProductID); // Store product ID in data attribute
    		dialog.style.display = 'flex';
	}

	function closeDialog() {
	    const dialog = document.getElementById('productDialog');
	    dialog.style.display = 'none';
	}
	
	
	//functions to reload the webpage and send POST data too:

	// Function to create and submit a form with POST method
	function postForm(path, params, method='post') {
	    // Create a form element
	    const form = document.createElement('form');
	    form.method = method;
	    form.action = path;

	    // Add the POST data to the form
	    for (const key in params) {
	        if (params.hasOwnProperty(key)) {
	            const hiddenField = document.createElement('input');
	            hiddenField.type = 'hidden';
	            hiddenField.name = key;
	            hiddenField.value = params[key];
	            form.appendChild(hiddenField);
	        }
	    }

	    // Add the form to the body and submit it
	    document.body.appendChild(form);
	    form.submit();
	}
	
	
	
	
	function confirmDelete() {
	    const productID = this.getAttribute('data-product-id'); // Retrieve the product ID from the button
	    if (window.confirm(`Wollen Sie wirklich das Produkt mit der Nummer ${productID} löschen? Hinweis: Es können nur Produkte gelöscht werden, welche nicht einer Waage zugeordnet sind.`)) {
	        console.log(`Product with ID ${productID} confirmed for deletion.`);
		// Implement deletion logic here, such as sending a request to a server
		
	    	  message = new Paho.MQTT.Message(productID);
		  message.destinationName = "homie/public_webpage_supplier/"+mqtt_user_name+"/cmd/delete_product";
		  console.log("Prepare Public Delete Product Message from Supplier: confirmDelete with parameter: "+productID)
		  mqtt.send(message);
		  console.log("Message successfully sent.")	

		
	        closeDialog(); // Close the dialog after confirmation
		
		alert("Deleted: "+productID);
	        //reload Webpage with POST data
		const postData = {
		    mqttusername: mqtt_user_name,
		    mqttpassword: mqtt_password
		};
		postForm('supplier_products.php', postData);
	    }
	}

	//document.getElementById('deleteButton').onclick = confirmDelete;



	</script>
	
	
    


            <h1>Hemmes24 Produktübersicht</h1>
            <p>Eingeloggt als: <?php echo $mqtt_user_name; ?></p>
	    <form action="supplier_full.php" method="POST">
	        <input type="hidden" name="mqttusername" value="<?php echo $mqtt_user_name; ?>">
	        <input type="hidden" name="mqttpassword" value="<?php echo $mqtt_password; ?>">
	        Ladenverwaltung: <button type="submit">Ladenübersicht</button>
	    </form>
	    <form action="supplier_products_new.php" method="POST">
	        <input type="hidden" name="mqttusername" value="<?php echo $mqtt_user_name; ?>">
	        <input type="hidden" name="mqttpassword" value="<?php echo $mqtt_password; ?>">
	        Ladenverwaltung: <button type="submit">Neues Produkt eintragen</button>
	    </form>

            <p id="mytext">...</p>

	    <p>&nbsp;</p>
	    <p>&nbsp;</p>
	    
	    <table id="productsTable" class="display">
	    <thead>
	        <tr>
	            <th>Name</th>
	            <th>Beschreibung</th>
	            <th>€/Einheit</th>
	            <th>kg/Einheit</th>
	            <th>MWSt.</th>
	            <th>Lieferant</th>
	        </tr>
	    </thead>
	    <tbody>
	        <!-- Rows will be added here -->
	    </tbody>
	</table>
	
	<script>
	function saveChanges() {
	    var productData = {
	        ProductName: document.getElementById('productName').value,
	        ProductDescription: document.getElementById('description').value,
	        PriceType: document.getElementById('priceType').value,
	        PricePerUnit: document.getElementById('pricePerUnit').value,
	        kgPerUnit: document.getElementById('kgPerUnit').value,
	        VAT: document.getElementById('vat').value,
	        Supplier: document.getElementById('supplier').value,
		ProductID: document.getElementById('productID').value
	    };

	    // Example of logging the data object to the console
	    console.log('Product Data:', productData);
	    
	    // Converting formData object into a JSON string
	    const productDataString = JSON.stringify(productData);
	    
    	  message = new Paho.MQTT.Message(productDataString);
	  message.destinationName = "homie/public_webpage_supplier/"+mqtt_user_name+"/cmd/edit_product";
	  console.log("Prepare Public Edit Product Message from Supplier: saveChanges with parameter: "+productDataString)
	  mqtt.send(message);
	  console.log("Message successfully sent.")	
	  alert("Produkt wurde geändert.");	
	  
		//reload Webpage with POST data
		const postData = {
		    mqttusername: mqtt_user_name,
		    mqttpassword: mqtt_password
		};
		postForm('supplier_products.php', postData);    

	}
	</script>
    
    
        <!-- Dialog Box -->
	<div id="productDialog" style="display:none;">
	    <form id="productForm">
	        <div id="dialogContent">
	            <!-- Form fields will be populated dynamically -->
	        </div>
	        <button type="button" onclick="closeDialog()">Close</button>
	        <button type="button" onclick="saveChanges()">Änderungen speichern</button>
		<button type="button" id="deleteButton">Delete</button>
	    </form>
	</div>


    
</body>

</html>
