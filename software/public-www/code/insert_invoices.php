<?php
include("invoices_cred.php");
define("My_DB_CHARSET", "utf8");

$servername = My_DB_HOST;  // or your host
$dbname = My_DB_NAME;  // your database name
$username = My_DB_USER;  // your database username
$password = My_DB_PASSWORD;  // your database password

if (array_key_exists('secret_key', $_POST)) {
  // Check if the secret key matches
  if ($_POST['secret_key'] !== $expected_secret_key) {
    die('Unauthorized request');
  }
} else {
    die('Unauthorized request');
}

// Create connection
$conn = new mysqli($servername, $username, $password, $dbname);

// Check connection
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Check if reset is needed for either table
if (isset($_POST['reset']) && $_POST['reset'] == 'true') {
    // SQL to delete and recreate the tables
    $resetSQL = "DROP TABLE IF EXISTS `Invoices`;
		CREATE TABLE `Invoices` (
		  `InvoiceID` int(11) NOT NULL,
		  `timestamp` timestamp NOT NULL DEFAULT current_timestamp(),
		  `ClientID` int(11) DEFAULT NULL,
		  `Products` text DEFAULT NULL,
		  `ProductsCount` int(11) DEFAULT 0,
		  `TotalAmount` decimal(10,2) DEFAULT 0.00
		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

		ALTER TABLE `Invoices`
		  ADD PRIMARY KEY (`InvoiceID`);


		DROP TABLE IF EXISTS `InvoiceProducts`;
		CREATE TABLE `InvoiceProducts` (
		  `InvoiceProductsID` int(11) NOT NULL,
		  `InvoiceID` int(11) DEFAULT NULL,
		  `ProductID` int(11) DEFAULT NULL,
		  `Supplier` varchar(50) NOT NULL,
		  `ProductName` varchar(255) DEFAULT NULL,
		  `ProductDescription` varchar(255) DEFAULT NULL,
		  `PriceType` int(11) DEFAULT NULL,
		  `PricePerUnit` decimal(10,2) DEFAULT NULL,
		  `kgPerUnit` decimal(10,2) DEFAULT NULL,
		  `WithdrawalUnits` int(11) DEFAULT NULL,
		  `Price` decimal(10,2) DEFAULT NULL,
		  `VAT` double NOT NULL DEFAULT 0.07
		);
		ALTER TABLE `InvoiceProducts`
		  ADD PRIMARY KEY (`InvoiceProductsID`);
		  
		ALTER TABLE `InvoiceProducts`
		  MODIFY `InvoiceProductsID` int(11) NOT NULL AUTO_INCREMENT;
		COMMIT;

                ";
    if ($conn->multi_query($resetSQL) === TRUE) {
        echo "Tables reset successfully.";
    } else {
        echo "Error resetting tables: " . $conn->error;
    }
    // Wait for multi queries to finish
    while ($conn->more_results() && $conn->next_result()) {
        // handle post-processing if needed
    }
}

$table = NULL;
if (array_key_exists("table", $_POST)) {
	$table = $_POST['table'];
}

// Continue to insert data if provided
if ($table=='Invoices') {
    // Variables from POST data for Invoices
    $InvoiceID = $_POST['InvoiceID'];
    $timestamp = $_POST['timestamp'];
    $clientID = NULL;
    if (array_key_exists("ClientID", $_POST)) {
      $clientID = $_POST['ClientID'];
    }
    $products = $_POST['Products'];
    $productsCount = $_POST['ProductsCount'];
    $totalAmount = $_POST['TotalAmount'];

    // Prepare and bind for Invoices table
    $stmt = $conn->prepare("INSERT INTO Invoices (InvoiceID, timestamp, ClientID, Products, ProductsCount, TotalAmount) VALUES (?, ?, ?, ?, ?, ?)");
    $stmt->bind_param("isisdd", $InvoiceID, $timestamp, $clientID, $products, $productsCount, $totalAmount);

    // Execute statement for Invoices
    if ($stmt->execute()) {
        echo "New Invoice record created successfully. ";
    } else {
        echo "Error: " . $stmt->error;
    }
    $stmt->close();
}
    
// Continue to insert data if provided
if ($table=='InvoiceProducts') {

	// Variables from POST data for InvoiceProducts
	$InvoiceID = $_POST['InvoiceID'];
	$productID = $_POST['ProductID'];
	$supplier = $_POST['Supplier'];
	$productName = $_POST['ProductName'];
	$productDescription = $_POST['ProductDescription'];
	$priceType = $_POST['PriceType'];
	$pricePerUnit = $_POST['PricePerUnit'];
	$kgPerUnit = $_POST['kgPerUnit'];
	$withdrawalUnits = $_POST['WithdrawalUnits'];
	$price = $_POST['Price'];
	$vat = $_POST['VAT'];

	// Prepare and bind for InvoiceProducts table
	$stmtProd = $conn->prepare("INSERT INTO InvoiceProducts (InvoiceID, ProductID, Supplier, ProductName, ProductDescription, PriceType, PricePerUnit, kgPerUnit, WithdrawalUnits, Price, VAT) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
	$stmtProd->bind_param("iisssdddidd", $InvoiceID, $productID, $supplier, $productName, $productDescription, $priceType, $pricePerUnit, $kgPerUnit, $withdrawalUnits, $price, $vat);


	// Execute statement for InvoiceProducts
	if ($stmtProd->execute()) {
	    echo "New InvoiceProduct record created successfully.";
	} else {
	    echo "Error: " . $stmtProd->error;
	}
	$stmtProd->close();
}

$conn->close();
?>
