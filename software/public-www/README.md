# Snippets for Wordpress

## Get User ID and display user QR-Code

```php
<?php
date_default_timezone_set("Europe/Berlin");
	
	$current_user = wp_get_current_user();
	$current_user_id = $current_user->ID;

$pdo = null;
$stmt = null;

$pdo = new PDO(
        "mysql:host=".My_DB_HOST.";dbname=".My_DB_NAME.";charset=".My_DB_CHARSET,
        My_DB_USER, My_DB_PASSWORD, [
          PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
          PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
        ]
      );
 
	$sql = "SELECT * FROM `address_book` WHERE `wp_id`=? ";
	$data = [$current_user_id];
    $stmt = $pdo->prepare($sql);
    $stmt->execute($data);
    $r = $stmt->fetch() ;

if ($r) {
	echo "<h2>Hallo ".$r["firstname"]." ".$r["name"]."!</h2>";
	
	$secret_str = "...";
	$t = abs(time());
	$id = $r["id"];
    $h = hash('md5', $secret_str.$t.$id, false);
    $h = substr($h,0,6);
	echo '<img  src="/qr/qr.php?level=L&size=10&text='.$t.'%20'.$id.'%20'.$h.'">';
	
	echo "<p>&nbsp;</p>";
	echo "<p>Dieser Code ist 10 Minunten gültig, bis: ";
	echo date("Y-m-d H:i:s",strtotime(date("Y-m-d H:i:s")." +10 minutes"));
	echo '.</p>';
	echo '<p>Zeit abgelaufen? <a href="/einlass">Seite neuladen!</a></p>';
	
	
	
} else {
	echo "<p>Aktuelle WP-Benutzer-ID: $current_user_id</p>";

	echo ("<p>Ihr Benutzerkonto wurde noch nicht freigeschaltet oder es ist ein Fehler dabei aufgetreten. Bitte kontaktieren Sie uns.</p>");
}
?>
```


## Redirect users

Ziel: Umleitung zur Einlass-Seite nach der Anmeldung in Wordpress

```php
function login_redirect( $redirect_to, $request, $user ){
    return home_url('/einlass');
}
add_filter( 'login_redirect', 'login_redirect', 10, 3 );
```


## Hide Adminbar for normal users

```php
add_action('after_setup_theme', 'remove_admin_bar');
function remove_admin_bar() {
if (!current_user_can('administrator') && !is_admin()) {
  show_admin_bar(false);
}
}
```


## class AddressBook()
```php
class AddressBook {
  // (A) CONSTRUCTOR - CONNECT TO DATABASE
  private $pdo = null;
  private $stmt = null;
  public $lastID = null;
  public $error = "";
  function __construct () {
    try {
      $this->pdo = new PDO(
        "mysql:host=".My_DB_HOST.";dbname=".My_DB_NAME.";charset=".My_DB_CHARSET,
        My_DB_USER, My_DB_PASSWORD, [
          PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
          PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
        ]
      );
    } catch (Exception $ex) { exit($ex->getMessage()); }
  }
 
  // (B) DESTRUCTOR - CLOSE DATABASE CONNECTION
  function __destruct () {
    if ($this->stmt!==null) { $this->stmt = null; }
    if ($this->pdo!==null) { $this->pdo = null; }
  }
 
  // (C) SAVE ENTRY
  function save ($title, $firstname, $name, $email, $tel, $addr, $postcode, $city, $wpid, $comment, $id=null) {
    // (C1) ADD NEW
    if ($id===null) {
	  $sql = "INSERT INTO `address_book` (`title`, `firstname`, `name`, `email`, `tel`, `address`, `postcode`, `city`, `wp_id`, `comment`) VALUES (?,?,?,?,?,?,?,?,?, ?)";
      $data = [$title, $firstname, $name, $email, $tel, $addr, $postcode, $city, $wpid, $comment];
    }
    // (C2) UPDATE
    else {
	  $sql = "UPDATE `address_book` SET `title`=?, `firstname`=?, `name`=?, `email`=?, `tel`=?, `address`=?, `postcode`=?, `city`=?, `wp_id`=?, `comment`=? WHERE `id`=?";
      $data = [$title, $firstname, $name, $email, $tel, $addr, $postcode, $city, $wpid, $comment, $id];
    }
    // (C3) RUN SQL
    try {
      $this->stmt = $this->pdo->prepare($sql);
      $this->stmt->execute($data);
      $this->lastID = $this->pdo->lastInsertId();
      return true;
    } catch (Exception $ex) {
      $this->error = $ex->getMessage();
      return false;
    }
  }
 
  // (D) DELETE ENTRY
  function del ($id) {
    try {
      $this->stmt = $this->pdo->prepare("DELETE FROM `address_book` WHERE `id`=?");
      $this->stmt->execute([$id]);
      return true;
    } catch (Exception $ex) {
      $this->error = $ex->getMessage();
      return false;
    }
  }

  // (E) GET ENTRY
  function get ($id=null) {
	$sql = "SELECT * FROM `address_book`" . ($id==null ? "" : " WHERE `id`=?") . " ORDER BY `name`, `firstname`";
	$data = $id==null ? null : [$id];
    $this->stmt = $this->pdo->prepare($sql);
    $this->stmt->execute($data);
    return $id==null ? $this->stmt->fetchAll() : $this->stmt->fetch() ;
  }
}
 
// (F) DATABASE SETTINGS - CHANGE TO YOUR OWN!
define("My_DB_HOST", "...");
define("My_DB_NAME", "...");
define("My_DB_CHARSET", "utf8");
define("My_DB_USER", "...");
define("My_DB_PASSWORD", "...");

// (G) NEW TO-DO OBJECT
//$_AB = new AddressBook();
```


## list address book
```php
<!-- (A) HEADER -->

<style>
.button1 {width: 150px;   background-color: #4CAF50; /* Green */}
.button2 {width: 150px;   background-color: #aa0000; /* red */}
</style>

<input type="button" value="Neuen Kunden anlegen" onclick="location.href='/intern/kunden/hinzufuegen/'"/>

<p>
	Sortierung ändern? Klicke auf die Tabellenspalten.
</p>
<!-- (B) LIST -->
<?php
$count = 0;
	$_AB = new AddressBook();
 
  // (B2) PROCESS DELETE ENTRY
  if (isset($_GET["del"])) {
    if ($_AB->del($_GET["del"])) {
      echo "<div class='note'>Kunde gelöscht</div>";
    } else {
      echo "<div class='note'>".$_AB->error."</div>";
    }
  }
 
  // (B3) LIST ENTRIES
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
    <th class="tg-fjir">ID/WP-ID</th>
    <th class="tg-fjir">Anrede</th>
    <th class="tg-fjir">Vorname</th>
    <th class="tg-fjir">Nachname</th>
    <th class="tg-fjir">E-Mail</th>
    <th class="tg-fjir">Straße</th>
    <th class="tg-fjir">PLZ</th>
    <th class="tg-fjir">Ort</th>
    <th class="tg-fjir">Telefon</th>
    <th class="tg-fjir">Kommentar</th>
  </tr>
</thead>
<tbody>
	<?php   
  $entries = $_AB->get();
  if (is_array($entries)) { foreach ($entries as $ab) { 
	$count++;?>
	  <tr>
    <td class="tg-0lax"><?=$ab["id"]?>/<?=$ab["wp_id"]?></td>
    <td class="tg-0lax"><?=$ab["title"]?></td>
    <td class="tg-0lax"><a href="/intern/kunden/hinzufuegen/?id=<?=$ab["id"]?>"><?=$ab["firstname"]?></a></td>
    <td class="tg-0lax"><a href="/intern/kunden/hinzufuegen/?id=<?=$ab["id"]?>"><?=$ab["name"]?></a></td>
    <td class="tg-0lax"><?=$ab["email"]?></td>
    <td class="tg-0lax"><?=$ab["address"]?></td>
    <td class="tg-0lax"><?=$ab["postcode"]?></td>
    <td class="tg-0lax"><?=$ab["city"]?></td>
    <td class="tg-0lax"><?=$ab["tel"]?></td>
    <td class="tg-0lax"><?=substr($ab["comment"],0,25)."..."?></td>
  </tr>
  <?php }} else { echo "No entries found."; }
?>

</tbody>
</table>

<p>
	Anzahl Kunden in Datenbank: <?=$count?>
</p>
```

## add / edit entry

```php
<style>
.button1 {width: 150px;   background-color: #4CAF50; /* Green */}
.button2 {width: 150px;   background-color: #aa0000; /* red */}
</style>

<?php
// (A) LOAD OBJECT
$_AB = new AddressBook();

// (B) PROCESS SAVE
if (isset($_POST["my_name"])) {
  //  function save ($title, $firstname, $name, $email, $tel, $addr, $postcode, $city, $wpid, $comment, $id=null) {
  if ($_AB->save($_POST["my_title"], $_POST["my_firstname"], $_POST["my_name"], $_POST["my_email"], $_POST["my_tel"], $_POST["my_addr"], $_POST["my_postcode"], $_POST["my_city"], $_POST["my_wpid"], $_POST["my_comment"], (isset($_GET["id"])?$_GET["id"]:null))) {
    header("Location: /intern/kunden/hinzufuegen/?s=1&id=" . (isset($_GET["id"])?$_GET["id"]:$_AB->lastID));
    exit();
  } else { echo "<div class='note'>{$_AB->error}</div>"; }
}
if (isset($_GET["s"])) { echo "<div class='note'>Kundeneintrag gespeichert</div>"; }

  // (B2) PROCESS DELETE ENTRY
  if (isset($_GET["del"])) {
    if ($_AB->del($_GET["del"])) {
      echo "<div class='note'>Kunde gelöscht</div>";
    } else {
      echo "<div class='note'>".$_AB->error."</div>";
    }
  }

// (C) ADDRESS BOOK ENTRY FORM
if (isset($_GET["id"])) { $entry = $_AB->get($_GET["id"]); } ?>
<input type="button" value="Zurück zur gesamten Kundenliste" onclick="location.href='/intern/kunden/'"/>

<form id="abform" method="post">
  <label for="my_name">Titel</label>                  <input type="text" name="my_title" required value="<?=isset($entry)?$entry["title"]:""?>"/>
  <label for="my_name">Vorname</label>                <input type="text" name="my_firstname" required value="<?=isset($entry)?$entry["firstname"]:""?>"/>
  <label for="my_name">Name</label>                   <input type="text" name="my_name" required value="<?=isset($entry)?$entry["name"]:""?>"/>
  <label for="my_email">E-Mail</label>                <input type="email" name="my_email" value="<?=isset($entry)?$entry["email"]:""?>"/>
  <label for="my_tel">Telefon</label>                 <input type="text" name="my_tel" value="<?=isset($entry)?$entry["tel"]:""?>"/>
  <label for="my_address">Address</label>             <input type="text" name="my_addr" value="<?=isset($entry)?$entry["address"]:""?>"/>
  <label for="my_name">PLZ</label>                    <input type="text" name="my_postcode"  value="<?=isset($entry)?$entry["postcode"]:""?>"/>
  <label for="my_name">Ort</label>                    <input type="text" name="my_city"  value="<?=isset($entry)?$entry["city"]:""?>"/>
  <label for="my_name">Wordpress-KontoID</label>      <input type="text" name="my_wpid"  value="<?=isset($entry)?$entry["wp_id"]:""?>"/>
  <label for="my_name">Kommentar</label>      <textarea name="my_comment"><?=isset($entry)?$entry["comment"]:""?></textarea>
 
  <input type="submit" class="button1" value="Änderungen Speichern"/>
  <input type="button" value="Zurück zur gesamten Kundenliste" onclick="location.href='/intern/kunden/'"/>
</form>
<p>
	&nbsp;
</p>
<hr>
<p>
	&nbsp;
</p>
<p>
	Mögliche, zur Verfügung stehende Wordpress-Konten:
</p>
<?php
$args1 = array(
 'orderby' => 'user_nicename',
 'order' => 'ASC'
);
 $subscribers = get_users($args1);
echo '<ul>';
 foreach ($subscribers as $user) {
 echo '<li>' . $user->display_name.' ['.$user->user_email . '] ('.$user->ID.')</li>';
 }
echo '</ul>';
?>
<?php
if (isset($_GET["id"])) { ?>
<hr>
<input type="button" value="Kunde löschen" onclick="if (confirm('Wirklich den Kunden unwiederbringlich löschen?')==true){location.href='?del=<?=$_GET["id"]?>';}"/>
<?php
}	
?>
```


## JS Sort Table
enable sortable HTML-tables
```php
<script>


var stIsIE = /*@cc_on!@*/false;

sorttable = {
  init: function() {
    // quit if this function has already been called
    if (arguments.callee.done) return;
    // flag this function so we don't do the same thing twice
    arguments.callee.done = true;
    // kill the timer
    if (_timer) clearInterval(_timer);

    if (!document.createElement || !document.getElementsByTagName) return;

    sorttable.DATE_RE = /^(\d\d?)[\/\.-](\d\d?)[\/\.-]((\d\d)?\d\d)$/;

    forEach(document.getElementsByTagName('table'), function(table) {
      if (table.className.search(/\bsortable\b/) != -1) {
        sorttable.makeSortable(table);
      }
    });

  },

  makeSortable: function(table) {
    if (table.getElementsByTagName('thead').length == 0) {
      // table doesn't have a tHead. Since it should have, create one and
      // put the first table row in it.
      the = document.createElement('thead');
      the.appendChild(table.rows[0]);
      table.insertBefore(the,table.firstChild);
    }
    // Safari doesn't support table.tHead, sigh
    if (table.tHead == null) table.tHead = table.getElementsByTagName('thead')[0];

    if (table.tHead.rows.length != 1) return; // can't cope with two header rows

    // Sorttable v1 put rows with a class of "sortbottom" at the bottom (as
    // "total" rows, for example). This is B&R, since what you're supposed
    // to do is put them in a tfoot. So, if there are sortbottom rows,
    // for backwards compatibility, move them to tfoot (creating it if needed).
    sortbottomrows = [];
    for (var i=0; i<table.rows.length; i++) {
      if (table.rows[i].className.search(/\bsortbottom\b/) != -1) {
        sortbottomrows[sortbottomrows.length] = table.rows[i];
      }
    }
    if (sortbottomrows) {
      if (table.tFoot == null) {
        // table doesn't have a tfoot. Create one.
        tfo = document.createElement('tfoot');
        table.appendChild(tfo);
      }
      for (var i=0; i<sortbottomrows.length; i++) {
        tfo.appendChild(sortbottomrows[i]);
      }
      delete sortbottomrows;
    }

    // work through each column and calculate its type
    headrow = table.tHead.rows[0].cells;
    for (var i=0; i<headrow.length; i++) {
      // manually override the type with a sorttable_type attribute
      if (!headrow[i].className.match(/\bsorttable_nosort\b/)) { // skip this col
        mtch = headrow[i].className.match(/\bsorttable_([a-z0-9]+)\b/);
        if (mtch) { override = mtch[1]; }
	      if (mtch && typeof sorttable["sort_"+override] == 'function') {
	        headrow[i].sorttable_sortfunction = sorttable["sort_"+override];
	      } else {
	        headrow[i].sorttable_sortfunction = sorttable.guessType(table,i);
	      }
	      // make it clickable to sort
	      headrow[i].sorttable_columnindex = i;
	      headrow[i].sorttable_tbody = table.tBodies[0];
	      dean_addEvent(headrow[i],"click", sorttable.innerSortFunction = function(e) {

          if (this.className.search(/\bsorttable_sorted\b/) != -1) {
            // if we're already sorted by this column, just
            // reverse the table, which is quicker
            sorttable.reverse(this.sorttable_tbody);
            this.className = this.className.replace('sorttable_sorted',
                                                    'sorttable_sorted_reverse');
            this.removeChild(document.getElementById('sorttable_sortfwdind'));
            sortrevind = document.createElement('span');
            sortrevind.id = "sorttable_sortrevind";
            sortrevind.innerHTML = stIsIE ? '&nbsp<font face="webdings">5</font>' : '&nbsp;&#x25B4;';
            this.appendChild(sortrevind);
            return;
          }
          if (this.className.search(/\bsorttable_sorted_reverse\b/) != -1) {
            // if we're already sorted by this column in reverse, just
            // re-reverse the table, which is quicker
            sorttable.reverse(this.sorttable_tbody);
            this.className = this.className.replace('sorttable_sorted_reverse',
                                                    'sorttable_sorted');
            this.removeChild(document.getElementById('sorttable_sortrevind'));
            sortfwdind = document.createElement('span');
            sortfwdind.id = "sorttable_sortfwdind";
            sortfwdind.innerHTML = stIsIE ? '&nbsp<font face="webdings">6</font>' : '&nbsp;&#x25BE;';
            this.appendChild(sortfwdind);
            return;
          }

          // remove sorttable_sorted classes
          theadrow = this.parentNode;
          forEach(theadrow.childNodes, function(cell) {
            if (cell.nodeType == 1) { // an element
              cell.className = cell.className.replace('sorttable_sorted_reverse','');
              cell.className = cell.className.replace('sorttable_sorted','');
            }
          });
          sortfwdind = document.getElementById('sorttable_sortfwdind');
          if (sortfwdind) { sortfwdind.parentNode.removeChild(sortfwdind); }
          sortrevind = document.getElementById('sorttable_sortrevind');
          if (sortrevind) { sortrevind.parentNode.removeChild(sortrevind); }

          this.className += ' sorttable_sorted';
          sortfwdind = document.createElement('span');
          sortfwdind.id = "sorttable_sortfwdind";
          sortfwdind.innerHTML = stIsIE ? '&nbsp<font face="webdings">6</font>' : '&nbsp;&#x25BE;';
          this.appendChild(sortfwdind);

	        // build an array to sort. This is a Schwartzian transform thing,
	        // i.e., we "decorate" each row with the actual sort key,
	        // sort based on the sort keys, and then put the rows back in order
	        // which is a lot faster because you only do getInnerText once per row
	        row_array = [];
	        col = this.sorttable_columnindex;
	        rows = this.sorttable_tbody.rows;
	        for (var j=0; j<rows.length; j++) {
	          row_array[row_array.length] = [sorttable.getInnerText(rows[j].cells[col]), rows[j]];
	        }
	        /* If you want a stable sort, uncomment the following line */
	        //sorttable.shaker_sort(row_array, this.sorttable_sortfunction);
	        /* and comment out this one */
	        row_array.sort(this.sorttable_sortfunction);

	        tb = this.sorttable_tbody;
	        for (var j=0; j<row_array.length; j++) {
	          tb.appendChild(row_array[j][1]);
	        }

	        delete row_array;
	      });
	    }
    }
  },

  guessType: function(table, column) {
    // guess the type of a column based on its first non-blank row
    sortfn = sorttable.sort_alpha;
    for (var i=0; i<table.tBodies[0].rows.length; i++) {
      text = sorttable.getInnerText(table.tBodies[0].rows[i].cells[column]);
      if (text != '') {
        if (text.match(/^-?[£$¤]?[\d,.]+%?$/)) {
          return sorttable.sort_numeric;
        }
        // check for a date: dd/mm/yyyy or dd/mm/yy
        // can have / or . or - as separator
        // can be mm/dd as well
        possdate = text.match(sorttable.DATE_RE)
        if (possdate) {
          // looks like a date
          first = parseInt(possdate[1]);
          second = parseInt(possdate[2]);
          if (first > 12) {
            // definitely dd/mm
            return sorttable.sort_ddmm;
          } else if (second > 12) {
            return sorttable.sort_mmdd;
          } else {
            // looks like a date, but we can't tell which, so assume
            // that it's dd/mm (English imperialism!) and keep looking
            sortfn = sorttable.sort_ddmm;
          }
        }
      }
    }
    return sortfn;
  },

  getInnerText: function(node) {
    // gets the text we want to use for sorting for a cell.
    // strips leading and trailing whitespace.
    // this is *not* a generic getInnerText function; it's special to sorttable.
    // for example, you can override the cell text with a customkey attribute.
    // it also gets .value for <input> fields.

    if (!node) return "";

    hasInputs = (typeof node.getElementsByTagName == 'function') &&
                 node.getElementsByTagName('input').length;

    if (node.getAttribute("sorttable_customkey") != null) {
      return node.getAttribute("sorttable_customkey");
    }
    else if (typeof node.textContent != 'undefined' && !hasInputs) {
      return node.textContent.replace(/^\s+|\s+$/g, '');
    }
    else if (typeof node.innerText != 'undefined' && !hasInputs) {
      return node.innerText.replace(/^\s+|\s+$/g, '');
    }
    else if (typeof node.text != 'undefined' && !hasInputs) {
      return node.text.replace(/^\s+|\s+$/g, '');
    }
    else {
      switch (node.nodeType) {
        case 3:
          if (node.nodeName.toLowerCase() == 'input') {
            return node.value.replace(/^\s+|\s+$/g, '');
          }
        case 4:
          return node.nodeValue.replace(/^\s+|\s+$/g, '');
          break;
        case 1:
        case 11:
          var innerText = '';
          for (var i = 0; i < node.childNodes.length; i++) {
            innerText += sorttable.getInnerText(node.childNodes[i]);
          }
          return innerText.replace(/^\s+|\s+$/g, '');
          break;
        default:
          return '';
      }
    }
  },

  reverse: function(tbody) {
    // reverse the rows in a tbody
    newrows = [];
    for (var i=0; i<tbody.rows.length; i++) {
      newrows[newrows.length] = tbody.rows[i];
    }
    for (var i=newrows.length-1; i>=0; i--) {
       tbody.appendChild(newrows[i]);
    }
    delete newrows;
  },

  /* sort functions
     each sort function takes two parameters, a and b
     you are comparing a[0] and b[0] */
  sort_numeric: function(a,b) {
    aa = parseFloat(a[0].replace(/[^0-9.-]/g,''));
    if (isNaN(aa)) aa = 0;
    bb = parseFloat(b[0].replace(/[^0-9.-]/g,''));
    if (isNaN(bb)) bb = 0;
    return aa-bb;
  },
  sort_alpha: function(a,b) {
    if (a[0]==b[0]) return 0;
    if (a[0]<b[0]) return -1;
    return 1;
  },
  sort_ddmm: function(a,b) {
    mtch = a[0].match(sorttable.DATE_RE);
    y = mtch[3]; m = mtch[2]; d = mtch[1];
    if (m.length == 1) m = '0'+m;
    if (d.length == 1) d = '0'+d;
    dt1 = y+m+d;
    mtch = b[0].match(sorttable.DATE_RE);
    y = mtch[3]; m = mtch[2]; d = mtch[1];
    if (m.length == 1) m = '0'+m;
    if (d.length == 1) d = '0'+d;
    dt2 = y+m+d;
    if (dt1==dt2) return 0;
    if (dt1<dt2) return -1;
    return 1;
  },
  sort_mmdd: function(a,b) {
    mtch = a[0].match(sorttable.DATE_RE);
    y = mtch[3]; d = mtch[2]; m = mtch[1];
    if (m.length == 1) m = '0'+m;
    if (d.length == 1) d = '0'+d;
    dt1 = y+m+d;
    mtch = b[0].match(sorttable.DATE_RE);
    y = mtch[3]; d = mtch[2]; m = mtch[1];
    if (m.length == 1) m = '0'+m;
    if (d.length == 1) d = '0'+d;
    dt2 = y+m+d;
    if (dt1==dt2) return 0;
    if (dt1<dt2) return -1;
    return 1;
  },

  shaker_sort: function(list, comp_func) {
    // A stable sort function to allow multi-level sorting of data
    // see: http://en.wikipedia.org/wiki/Cocktail_sort
    // thanks to Joseph Nahmias
    var b = 0;
    var t = list.length - 1;
    var swap = true;

    while(swap) {
        swap = false;
        for(var i = b; i < t; ++i) {
            if ( comp_func(list[i], list[i+1]) > 0 ) {
                var q = list[i]; list[i] = list[i+1]; list[i+1] = q;
                swap = true;
            }
        } // for
        t--;

        if (!swap) break;

        for(var i = t; i > b; --i) {
            if ( comp_func(list[i], list[i-1]) < 0 ) {
                var q = list[i]; list[i] = list[i-1]; list[i-1] = q;
                swap = true;
            }
        } // for
        b++;

    } // while(swap)
  }
}

/* ******************************************************************
   Supporting functions: bundled here to avoid depending on a library
   ****************************************************************** */

// Dean Edwards/Matthias Miller/John Resig

/* for Mozilla/Opera9 */
if (document.addEventListener) {
    document.addEventListener("DOMContentLoaded", sorttable.init, false);
}

/* for Internet Explorer */
/*@cc_on @*/
/*@if (@_win32)
    document.write("<script id=__ie_onload defer src=javascript:void(0)><\/script>");
    var script = document.getElementById("__ie_onload");
    script.onreadystatechange = function() {
        if (this.readyState == "complete") {
            sorttable.init(); // call the onload handler
        }
    };
/*@end @*/

/* for Safari */
if (/WebKit/i.test(navigator.userAgent)) { // sniff
    var _timer = setInterval(function() {
        if (/loaded|complete/.test(document.readyState)) {
            sorttable.init(); // call the onload handler
        }
    }, 10);
}

/* for other browsers */
window.onload = sorttable.init;

// written by Dean Edwards, 2005
// with input from Tino Zijdel, Matthias Miller, Diego Perini

// http://dean.edwards.name/weblog/2005/10/add-event/

function dean_addEvent(element, type, handler) {
	if (element.addEventListener) {
		element.addEventListener(type, handler, false);
	} else {
		// assign each event handler a unique ID
		if (!handler.$$guid) handler.$$guid = dean_addEvent.guid++;
		// create a hash table of event types for the element
		if (!element.events) element.events = {};
		// create a hash table of event handlers for each element/event pair
		var handlers = element.events[type];
		if (!handlers) {
			handlers = element.events[type] = {};
			// store the existing event handler (if there is one)
			if (element["on" + type]) {
				handlers[0] = element["on" + type];
			}
		}
		// store the event handler in the hash table
		handlers[handler.$$guid] = handler;
		// assign a global event handler to do all the work
		element["on" + type] = handleEvent;
	}
};
// a counter used to create unique IDs
dean_addEvent.guid = 1;

function removeEvent(element, type, handler) {
	if (element.removeEventListener) {
		element.removeEventListener(type, handler, false);
	} else {
		// delete the event handler from the hash table
		if (element.events && element.events[type]) {
			delete element.events[type][handler.$$guid];
		}
	}
};

function handleEvent(event) {
	var returnValue = true;
	// grab the event object (IE uses a global event object)
	event = event || fixEvent(((this.ownerDocument || this.document || this).parentWindow || window).event);
	// get a reference to the hash table of event handlers
	var handlers = this.events[event.type];
	// execute each event handler
	for (var i in handlers) {
		this.$$handleEvent = handlers[i];
		if (this.$$handleEvent(event) === false) {
			returnValue = false;
		}
	}
	return returnValue;
};

function fixEvent(event) {
	// add W3C standard event methods
	event.preventDefault = fixEvent.preventDefault;
	event.stopPropagation = fixEvent.stopPropagation;
	return event;
};
fixEvent.preventDefault = function() {
	this.returnValue = false;
};
fixEvent.stopPropagation = function() {
  this.cancelBubble = true;
}

// Dean's forEach: http://dean.edwards.name/base/forEach.js
/*
	forEach, version 1.0
	Copyright 2006, Dean Edwards
	License: http://www.opensource.org/licenses/mit-license.php
*/

// array-like enumeration
if (!Array.forEach) { // mozilla already supports this
	Array.forEach = function(array, block, context) {
		for (var i = 0; i < array.length; i++) {
			block.call(context, array[i], i, array);
		}
	};
}

// generic enumeration
Function.prototype.forEach = function(object, block, context) {
	for (var key in object) {
		if (typeof this.prototype[key] == "undefined") {
			block.call(context, object[key], key, object);
		}
	}
};

// character enumeration
String.forEach = function(string, block, context) {
	Array.forEach(string.split(""), function(chr, index) {
		block.call(context, chr, index, string);
	});
};

// globally resolve forEach enumeration
var forEach = function(object, block, context) {
	if (object) {
		var resolve = Object; // default
		if (object instanceof Function) {
			// functions have a "length" property
			resolve = Function;
		} else if (object.forEach instanceof Function) {
			// the object implements a custom forEach method so use that
			object.forEach(block, context);
			return;
		} else if (typeof object == "string") {
			// the object is a string
			resolve = String;
		} else if (typeof object.length == "number") {
			// the object is array-like
			resolve = Array;
		}
		resolve.forEach(object, block, context);
	}
};

</script>
```
