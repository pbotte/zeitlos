<?php
include("invoices_cred.php");
define("My_DB_CHARSET", "utf8");


if (array_key_exists('secret', $_GET)) {
  // Check if the secret key matches
  if ($_GET['secret'] !== $expected_secret_key) {
    die('Unauthorized request');
  }
} else {
    die('Unauthorized request');
}
?>


<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Invoice Details</title>
    <style>
        table, th, td {
            border: 1px solid black;
            border-collapse: collapse;
        }
        th, td {
            padding: 8px;
            text-align: left;
        }
    </style>
    <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/2.0.3/css/dataTables.dataTables.css">
    <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/datetime/1.5.2/css/dataTables.dateTime.min.css">
    <script type="text/javascript" src="https://code.jquery.com/jquery-3.7.1.js"></script>
    <script type="text/javascript" src="https://cdn.datatables.net/2.0.3/js/dataTables.js"></script>
    <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.2/moment.min.js"></script>
    <script type="text/javascript" src="https://cdn.datatables.net/datetime/1.5.2/js/dataTables.dateTime.min.js"></script>
    
</head>
<body>
    <h1>Invoice Details</h1>
    <table border="0" cellspacing="5" cellpadding="5">
        <tbody><tr>
            <td>Minimum date:</td>
            <td><input type="text" id="min" name="min"></td>
        </tr>
        <tr>
            <td>Maximum date:</td>
            <td><input type="text" id="max" name="max"></td>
        </tr>
    </tbody></table>
    <table id="myTable">
        <thead>
            <tr>
                <th>InvoiceID</th>
                <th>Timestamp</th>
                <th>ProductsCount</th>
                <th>TotalAmount</th>
                <th>ProductID</th>
                <th>Supplier</th>
                <th>ProductName</th>
                <th>ProductDescription</th>
                <th>Price</th>
                <th>VAT</th>
                <th>WithdrawalUnits</th>
            </tr>
        </thead>
        <tbody>
            <?php
            // Database connection parameters
            $host = My_DB_HOST;  // or your host
            $dbname = My_DB_NAME;  // your database name
            $username = My_DB_USER;  // your database username
            $password = My_DB_PASSWORD;  // your database password

            // DSN for MariaDB connection using PDO
            $dsn = "mysql:host=$host;dbname=$dbname;charset=utf8mb4";

            try {
                // Create a PDO instance as db connection to MariaDB
                $pdo = new PDO($dsn, $username, $password);
                $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

                // Query to select data from Invoices table joined with InvoiceProducts
                $sql = "SELECT i.InvoiceID, i.timestamp, i.ProductsCount, i.TotalAmount,
                                p.ProductID, p.Supplier, p.ProductName, p.ProductDescription, p.Price, p.VAT, p.WithdrawalUnits
                        FROM Invoices i
                        LEFT JOIN InvoiceProducts p ON i.InvoiceID = p.InvoiceID
                        ORDER BY i.InvoiceID, p.ProductID";
                $stmt = $pdo->query($sql);

                // Check if we have any invoices
                if ($stmt->rowCount() > 0) {
                    // Output data of each row
                    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
                        echo "<tr>";
                        echo "<td>" . htmlspecialchars($row["InvoiceID"]) . "</td>";
                        if (!is_null($row["timestamp"])) {echo "<td>" . htmlspecialchars($row["timestamp"]) . "</td>";} else {echo "<td></td>";}
                        if (!is_null($row["ProductsCount"])) {echo "<td>" . htmlspecialchars($row["ProductsCount"]) . "</td>";} else {echo "<td></td>";}
                        if (!is_null($row["TotalAmount"])) {echo "<td>" . htmlspecialchars($row["TotalAmount"]) . "</td>";} else {echo "<td></td>";}
                        if (!is_null($row["ProductID"])) {echo "<td>" . htmlspecialchars($row["ProductID"]) . "</td>";} else {echo "<td></td>";}
                        if (!is_null($row["Supplier"])) {echo "<td>" . htmlspecialchars($row["Supplier"]) . "</td>";} else {echo "<td></td>";}
                        if (!is_null($row["ProductName"])) {echo "<td>" . htmlspecialchars($row["ProductName"]) . "</td>";} else {echo "<td></td>";}
                        if (!is_null($row["ProductDescription"])) {echo "<td>" . htmlspecialchars($row["ProductDescription"]) . "</td>";} else {echo "<td></td>";}
                        if (!is_null($row["Price"])) {echo "<td>" . htmlspecialchars($row["Price"]) . "</td>";} else {echo "<td></td>";}
                        if (!is_null($row["VAT"])) {echo "<td>" . htmlspecialchars($row["VAT"]) . "</td>";} else {echo "<td></td>";}
                        if (!is_null($row["WithdrawalUnits"])) {echo "<td>" . htmlspecialchars($row["WithdrawalUnits"]) . "</td>";} else {echo "<td></td>";}
                        echo "</tr>";
                    }
                } else {
                    echo "<tr><td colspan='11'>No results found</td></tr>";
                }

            } catch (PDOException $e) {
                die("Could not connect to the database $dbname :" . $e->getMessage());
            }
            ?>
        </tbody>
    </table>

    <script>
let minDate, maxDate;
 
 // Custom filtering function which will search data in column four between two values
 DataTable.ext.search.push(function (settings, data, dataIndex) {
     let min = minDate.val();
     let max = maxDate.val();
     let date = new Date(data[1]);
  
     if (
         (min === null && max === null) ||
         (min === null && date <= max) ||
         (min <= date && max === null) ||
         (min <= date && date <= max)
     ) {
         return true;
     }
     return false;
 });
  
 // Create date inputs
 minDate = new DateTime('#min', {
     format: 'MMMM Do YYYY'
 });
 maxDate = new DateTime('#max', {
     format: 'MMMM Do YYYY'
 });
  
 // DataTables initialisation
 let table = new DataTable('#myTable');
  
 // Refilter the table
 document.querySelectorAll('#min, #max').forEach((el) => {
     el.addEventListener('change', () => table.draw());
 });
        
    </script>
</body>
</html>
