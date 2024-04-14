<?php

define("My_DB_HOST", "192.168.10.10");
define("My_DB_NAME", "zeitlos");
define("My_DB_CHARSET", "utf8");
define("My_DB_USER", "user_shop_control");
define("My_DB_PASSWORD", "wlLvMOR4FStMEzzN");

$pdo = null;
$stmt = null;

$pdo = new PDO(
        "mysql:host=".My_DB_HOST.";dbname=".My_DB_NAME.";charset=".My_DB_CHARSET,
        My_DB_USER, My_DB_PASSWORD, [
          PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
          PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
        ]
      );

	$sql = "SELECT * FROM `Invoices` ";
	$data = [];
    $stmt = $pdo->prepare($sql);
    $stmt->execute($data);
    $r = $stmt->fetchAll() ;


?>
<style type="text/css">
.tg  {border-collapse:collapse;border-spacing:0;}
.tg td{border-color:black;border-style:solid;border-width:1px;color:#000000;font-family:Arial, sans-serif;font-size:14px;
  overflow:hidden;padding:10px 5px;word-break:normal;}
.tg th{border-color:black;border-style:solid;border-width:1px;font-family:Arial, sans-serif;font-size:14px;
  font-weight:normal;overflow:hidden;padding:10px 5px;word-break:normal;}
.tg tr:nth-child(even) {background: #EEEEEE}
.tg tr:nth-child(odd) {background: #FFFFF}
.tg .tg-fjir{background-color:#343434;color:#ffffff;text-align:left;vertical-align:top}
.tg .tg-0lax{text-align:left;vertical-align:top}
</style>

<table class="tg sortable" >
<thead>
  <tr>
    <th class="tg-fjir">ID</th>
    <th class="tg-fjir">Uhrzeit</th>
    <th class="tg-fjir">Kunden-Nr</th>
    <th class="tg-fjir">Products</th>
  </tr>
</thead>
<tbody>
	<?php
  $entries = $r;
  if (is_array($entries)) { foreach ($entries as $ab) { 
	$count++;?>
	  <tr>
    <td class="tg-0lax"><?=$ab["InvoiceID"]?></td>
    <td class="tg-0lax"><?=$ab["timestamp"]?></td>
    <td class="tg-0lax"><a href="https://www.hemmes24.de/intern/kunden/hinzufuegen/?id=<?=$ab["ClientID"]?>">Kundennr. <?=$ab["ClientID"]?></a></td>
    <td class="tg-0lax"><?php
$p = json_decode($ab["Products"], true);
$i = 0;
if (!is_null($p)) {
  foreach ($p['data'] as $v) {
    $i++;
    print($v["withdrawal_units"]."x ".$v["ProductName"]." (".$v['ProductDescription'].") (".$v['kgPerUnit']."kg/Stk) à ".number_format($v['PricePerUnit'],2)."€ = ".number_format($v['price'],2)."€ <br>");
/*PriceType
kgPerUnit */
  }
}
if ($i==0) {echo "<p>Keine Produkte gekauft.</p>"; }
?></td>
  </tr>
  <?php }} else { echo "No entries found."; }
?>

</tbody>
</table>
