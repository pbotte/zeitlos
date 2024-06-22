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
    <title>Tagesübersichten</title>
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
    
</head>
<body>
    <h1>Tagesübersichten</h1>

    <table id="myTable">
        <thead>
            <tr>
                <th>Datum</th>
                <th>Tagesumsatz</th>
                <th>Tagessteuer</th>
                <th>Umsatz 0%</th>
                <th>MwSt 0%</th>
                <th>Umsatz 7%</th>
                <th>MwSt 7%</th>
                <th>Umsatz 19%</th>
                <th>MwSt 19%</th>
            </tr>
        </thead>
        <tbody>
            <?php
	    $fmt = numfmt_create( 'de_DE', NumberFormatter::CURRENCY );
	    
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
                $sql = "SELECT DATE(DATE_SUB(i.timestamp, INTERVAL 3 HOUR)) as Date, 
				SUM(p.Price) as Total_Amount, 
			       SUM(CASE WHEN p.VAT = 0 THEN p.Price ELSE 0 END) as Total_Price_VAT_0,
			       SUM(CASE WHEN p.VAT = 0.07 THEN p.Price ELSE 0 END) as Total_Price_VAT_07,
			       SUM(CASE WHEN p.VAT = 0.19 THEN p.Price ELSE 0 END) as Total_Price_VAT_19
			FROM Invoices i
			LEFT JOIN InvoiceProducts p ON i.InvoiceID = p.InvoiceID
			GROUP BY Date
			ORDER BY Date;";
                $stmt = $pdo->query($sql);

                // Check if we have any invoices
                if ($stmt->rowCount() > 0) {
                    // Output data of each row
                    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
		    	$Total_VAT_Amount_0 =  round($row["Total_Price_VAT_0"] * 0, 2);
		    	$Total_VAT_Amount_07 = round($row["Total_Price_VAT_07"] * (1- 1 / 1.07), 2);
		    	$Total_VAT_Amount_19 = round($row["Total_Price_VAT_19"] * (1- 1 / 1.19), 2);
			$Total_VAT_Amount_All = $Total_VAT_Amount_0 + $Total_VAT_Amount_07 + $Total_VAT_Amount_19;
                        echo "<tr>";
                        if (!is_null($row["Date"])) {echo "<td>" . htmlspecialchars($row["Date"]) . "</td>";} else {echo "<td></td>";}
                        if (!is_null($row["Total_Amount"])) {echo "<td>" . numfmt_format_currency($fmt, $row["Total_Amount"], "EUR") . "</td>";} else {echo "<td></td>";}
                        echo "<td>" . numfmt_format_currency($fmt, $Total_VAT_Amount_All, "EUR") . "</td>";
                        if (!is_null($row["Total_Price_VAT_0"])) {echo "<td>" . numfmt_format_currency($fmt, $row["Total_Price_VAT_0"], "EUR") . "</td>";} else {echo "<td></td>";}
                        echo "<td>" . numfmt_format_currency($fmt, $Total_VAT_Amount_0, "EUR") . "</td>";
                        if (!is_null($row["Total_Price_VAT_07"])) {echo "<td>" . numfmt_format_currency($fmt, $row["Total_Price_VAT_07"], "EUR") . "</td>";} else {echo "<td></td>";}
                        echo "<td>" . numfmt_format_currency($fmt, $Total_VAT_Amount_07, "EUR") . "</td>";
                        if (!is_null($row["Total_Price_VAT_19"])) {echo "<td>" . numfmt_format_currency($fmt, $row["Total_Price_VAT_19"], "EUR") . "</td>";} else {echo "<td></td>";}
                        echo "<td>" . numfmt_format_currency($fmt, $Total_VAT_Amount_19, "EUR") . "</td>";
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

</body>
</html>
