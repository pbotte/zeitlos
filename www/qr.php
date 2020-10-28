<?php
    include "qr/lib/full/qrlib.php";
 
    $errorCorrectionLevel = 'L';
    if (isset($_GET['level']) && in_array($_GET['level'], array('L','M','Q','H')))
        $errorCorrectionLevel = $_GET['level'];
 
    $matrixPointSize = 4;
    if (isset($_GET['size']))
        $matrixPointSize = min(max((int)$_GET['size'], 1), 10);
 
    $textData = 'Beispieltext';
 
    if (isset($_GET['text']) && (trim($_GET['text']) != '')) {
        $textData = $_GET['text'];
    }
 
    QRcode::png($textData, false, $errorCorrectionLevel, $matrixPointSize, 0); // Die letzte 0 ist die Dicke des weißen Rahmens
?>

