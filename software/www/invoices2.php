<?php
define("My_DB_HOST", "192.168.10.10");
define("My_DB_NAME", "zeitlos");
define("My_DB_CHARSET", "utf8");
define("My_DB_USER", "user_shop_control");
define("My_DB_PASSWORD", "wlLvMOR4FStMEzzN");
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
</head>
<body>
    <h1>Invoice Details</h1>
    <table>
        <thead>
            <tr>
                <th>InvoiceID</th>
                <th>ClientID</th>
                <th>ProductsCount</th>
                <th>TotalAmount</th>
                <th>Product Details</th>
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

                // Query to select data from Invoices table
                $stmt = $pdo->query("SELECT InvoiceID, ClientID, ProductsCount, TotalAmount FROM Invoices");

                // Check if we have any invoices
                if ($stmt->rowCount() > 0) {
                    // Output data of each row
                    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
                        echo "<tr>";
                        echo "<td>" . htmlspecialchars($row["InvoiceID"]) . "</td>";
                        echo "<td>" . htmlspecialchars($row["ClientID"]) . "</td>";
                        echo "<td>" . htmlspecialchars($row["ProductsCount"]) . "</td>";
                        echo "<td>" . htmlspecialchars($row["TotalAmount"]) . "</td>";

                        // Fetch related products
                        $productStmt = $pdo->prepare("SELECT * FROM InvoiceProducts WHERE InvoiceID = ?");
                        $productStmt->execute([$row["InvoiceID"]]);
                        echo "<td>";
                        if ($productStmt->rowCount() > 0) {
                            echo "<ul>";
                            while ($productRow = $productStmt->fetch(PDO::FETCH_ASSOC)) {
                                echo "<li>ProductID: " . htmlspecialchars($productRow["ProductID"])
                                     . ", Name: " . htmlspecialchars($productRow["ProductName"])
                                     . ", Description: " . htmlspecialchars($productRow["ProductDescription"])
                                     . ", Price: $" . htmlspecialchars($productRow["Price"])
                                     . ", Units: " . htmlspecialchars($productRow["WithdrawalUnits"]) . "</li>";
                            }
                            echo "</ul>";
                        } else {
                            echo "No products found";
                        }
                        echo "</td>";

                        echo "</tr>";
                    }
                } else {
                    echo "<tr><td colspan='6'>No results found</td></tr>";
                }

            } catch (PDOException $e) {
                die("Could not connect to the database $dbname :" . $e->getMessage());
            }
            ?>
        </tbody>
    </table>
</body>
</html>
