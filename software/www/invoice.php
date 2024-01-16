<?php

$add_text = "";
$add_products = array();
$timestamp = 0;

$SECRETSTR= "blablablaskfjshfushdfisuh5487wzfisaubsidab";

//Load data from user via URL
$entered_check_str = "";
if (array_key_exists("c", $_GET)) {
  $entered_check_str = $_GET["c"];
}
$data_str = "";
if (array_key_exists("d", $_GET)) {
  $data_str = $_GET['d'];
}

//Check whether check is okay:
$check_ok = false;
$correct_check_str = "";
if (array_key_exists("d", $_GET)) {
  $str_to_check = $SECRETSTR.$data_str;
  $correct_check_str = hash('crc32b', $str_to_check, false);

  if ($correct_check_str == $entered_check_str) $check_ok = true;
}
if ($check_ok == false) {
  echo "<pre>data_str: $data_str\nentered_check_str: $entered_check_str\ncorrect_check_str: $correct_check_str</pre>";
  throw new Exception('check string not valid.');
}

//Start decoding
$data_str_decoded = gzuncompress(base64_decode(strtr($data_str, '-_', '+/')));

  
$data = json_decode($data_str_decoded, true);
if (empty($data)) {
  echo "<pre>data_str_decoded: $data_str_decoded</pre>";
  echo "<pre>";
  var_dump($data);
  echo "</pre>";
  throw new Exception('data array empty. Most likely the JSON string is invalid.');
}
  
$add_text = $data['d']['c'];
if (array_key_exists('p', $data['d'])) {
  $rechnungs_posten = $data['d']['p'];
}
if (array_key_exists('t', $data['d'])) {
  $timestamp = $data['d']['t'];
}


//Auflistung verschiedenen Posten im Format [Produktbezeichnung, Menge, Einzelpreis, MWSt.-Klasse]
/*$rechnungs_posten = array(
  array("Produkt 1", 1, 42.50, 0),
  array("Produkt 2", 5, 5.20, 1),
  array("Birnen", 3, 2.20, 2),
  array("Produkt 3", 3, 10.00, 2)
  );
*/

 
$rechnungs_header = '
<p align="center">
<img src="../wp-content/uploads/2022/09/cropped-HEMMES_Marke_neg_cmyk_c_Zeichenflaeche-1.png" width="4cm">
<b>HEMMES24</b>
Thomas Hemmes
Edelobstbrennerei Hemmes 
Gartenfeldstr. 1
55435 Gau-Algesheim
Deutschland 
Tel.: 067254924
E‑Mail: info@hemmes.de 
UST. ID-Nr.: DE 197966562
www.hemmes24.de
</p>';

$html = nl2br(trim($rechnungs_header));
  

if (isset($rechnungs_posten)) {
	if (count($rechnungs_posten)>0) {
		$html .= '
		<br>

		<hr>
		<table cellpadding="1" cellspacing="0" style="width: 100%;" border="0">
		<tr>
			<td>Kasse</td>
			<td style="text-align: right;">Zeitpunkt</td>
		</tr>
		<tr>
			<td>001</td>
			<td style="text-align: right;">'.date('d.m.y H:i:s', $timestamp).'</td>
		</tr>
		</table>
		<hr>';
		$html .='
		<br>&nbsp;
		<br>

		<table cellpadding="1" cellspacing="0" style="width: 100%;" border="0">
		<tr style="background-color: #cccccc; padding:1px;">
		<td style="padding:1px;" width="70%"><b>Ihr Einkauf</b></td>
		<td style="text-align: right;" width="30%"><b>€&nbsp;&nbsp;&nbsp;</b></td>
		</tr>';
	
	
	
	
		$gesamtpreis = 0;
		$USt_sum = array(0,0,0); //0%, reduced tax, full tax rate

		foreach($rechnungs_posten as $posten) {
		$menge = $posten[1];
		$einzelpreis = $posten[2];
		$preis = $menge*$einzelpreis;
		$gesamtpreis += $preis;
	
	
		if ($posten[3] == 0) {
			$USt_sum[$posten[3]] += $preis;
		} elseif ($posten[3] == 1) {
			$USt_sum[$posten[3]] += $preis;
		} else {
			$USt_sum[$posten[3]] += $preis;
		}
	
		$html .= '<tr>
						<td>'.$posten[1].'x '.$posten[0];
		if ($posten[1] > 1) { 
			$html .= ' à '.number_format($posten[2], 2, ',', '').'€';
		}
		$html .= '</td>
						<td style="text-align: right;">'.number_format($preis, 2, ',', '').'&nbsp;'.$posten[3].'</td>
					</tr>';
		}
		$html .="</table>";
	
	
		$html .= '
		<hr>
		<table cellpadding="5" cellspacing="0" style="width: 100%;" border="0">
		<tr>
		<td colspan="3"><b>Summe:</b></td>
		<td style="text-align: center;"><b>'.number_format($gesamtpreis, 2, ',', '').'</b></td>
		</tr>
		</table>

		<br>

		<p align="center">Vielen Dank für Ihren Einkauf!</p>

		<br><br>

		<hr>
		<table cellpadding="1" cellspacing="0" style="width: 100%;" border="0">
		<tr>
			<td>UST</td>
			<td style="text-align: right;">Netto</td>
			<td style="text-align: right;">Steuer</td>
			<td style="text-align: right;">Brutto</td>
		</tr>
		<tr>
			<td>0 = 0%</td>
			<td style="text-align: right;">'.number_format($USt_sum[0]*(1-0.00), 2, ',', '').'</td>
			<td style="text-align: right;">'.number_format($USt_sum[0]*0 , 2, ',', '').'</td>
			<td style="text-align: right;">'.number_format($USt_sum[0] , 2, ',', '').'</td>
		</tr>
		<tr>
			<td>1 = 7%</td>
			<td style="text-align: right;">'.number_format($USt_sum[1]*(1-0.07), 2, ',', '').'</td>
			<td style="text-align: right;">'.number_format($USt_sum[1]*0.07, 2, ',', '').'</td>
			<td style="text-align: right;">'.number_format($USt_sum[1], 2, ',', '').'</td>
		</tr>
		<tr>
			<td>2 = 19%</td>
			<td style="text-align: right;">'.number_format($USt_sum[2]*(1-0.19), 2, ',', '').'</td>
			<td style="text-align: right;">'.number_format($USt_sum[2]*0.19, 2, ',', '').'</td>
			<td style="text-align: right;">'.number_format($USt_sum[2], 2, ',', '').'</td>
		</tr>
		</table>
		<hr>

		';
	}
} 

 
$rechnungs_footer = '


<pre>
'.$add_text.'
</pre>
';

$html .= $rechnungs_footer;
 
 
 
 
// TCPDF Library laden
require_once('tcpdf/tcpdf.php');
 
// Erstellung des PDF Dokuments
// $pdf = new TCPDF(PDF_PAGE_ORIENTATION, PDF_UNIT, PDF_PAGE_FORMAT, true, 'UTF-8', false);
$pdf = new TCPDF(PDF_PAGE_ORIENTATION, PDF_UNIT, array(72, 200), true, 'UTF-8', false);


// Dokumenteninformationen
$pdf->SetCreator(PDF_CREATOR);
$pdf->SetAuthor("zeitlos");
$pdf->SetTitle('Rechnung');
$pdf->SetSubject('Rechnung');
 
// remove default header/footer
$pdf->setPrintHeader(false);
$pdf->setPrintFooter(false);
 
// Header und Footer Informationen
$pdf->setHeaderFont(Array(PDF_FONT_NAME_MAIN, '', PDF_FONT_SIZE_MAIN));
$pdf->setFooterFont(Array(PDF_FONT_NAME_DATA, '', PDF_FONT_SIZE_DATA));
 
// Auswahl des Font
$pdf->SetDefaultMonospacedFont(PDF_FONT_MONOSPACED);
 
// Auswahl der MArgins
$pdf->SetMargins(1 /*LEFT*/, 2 /*TOP*/, 1 /*RIGHT*/);
$pdf->SetHeaderMargin(5);
$pdf->SetFooterMargin(10);
 
// Automatisches Autobreak der Seiten
$pdf->SetAutoPageBreak(TRUE, 1);
 
// Image Scale 
$pdf->setImageScale(PDF_IMAGE_SCALE_RATIO);
 
$pdf->SetFont('dejavusans', '', 10);
 
$pdf->AddPage();
 
$pdf->writeHTML($html, true, false, true, false, '');


 
 
//output PDF

$output_method = 0;
if (array_key_exists("out", $_GET)) {
	if ($_GET["out"] ==  "pdf") $output_method = 0;
	if ($_GET["out"] ==  "html") $output_method = 1;
	if ($_GET["out"] ==  "download") $output_method = 2;
} 

if ($output_method == 0) {
	//Variante 1: PDF direkt an den Benutzer senden:
	$pdf->Output("rechnung.pdf", 'I');
}

if ($output_method == 1) {
	//Variante 2: output as HTML
	?>
	<table border="1" style="border-collapse: collapse; width: 100%; max-width: 300px; border: 1px solid black;">
	  <tr>
	    <td><?= $html?></td>
	  </tr>
	</table>

	<?php
}
 
if ($output_method == 2) {
	//Variante 3: PDF im Verzeichnis abspeichern:
	$pdf->Output(dirname(__FILE__).'/'.$pdfName, 'F');
	echo 'Download PDF: <a href="'.$pdfName.'">'.$pdfName.'</a>';
}
 
?>