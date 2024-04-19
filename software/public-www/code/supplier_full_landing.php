<html>
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
    
        body {
            font-family: Arial, sans-serif; /* Sets a clean, modern font */
            background-color: #f4f4f4; /* Light grey background */
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
	h2 {
            text-align: center;
            color: #333;
            margin-bottom: 20px; /* Adds space below the headline */
        }
        form {
            background-color: #fff;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1); /* Adds subtle shadow */
            border-radius: 8px;
            width: 300px;
            display: flex;
            flex-direction: column;
            align-items: center; /* Centers form elements vertically */
        }
        div {
            width: 100%; /* Ensures div elements span full width of the form */
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        button {
            width: 100%;
            padding: 10px;
            background-color: #5c67f2; /* A pleasant blue */
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #4a54e1; /* Darker shade on hover */
        }
</style>

<head>
    <title>Lieferanten Zugang</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>

<body>
    <form action="/code/supplier_full.php" method="post">
        <h2>Hemmes24 Lieferantenzugang</h2>
        <div>
            <label for="username">Benutzername:</label>
            <input type="text" id="username" name="mqttusername" required>
        </div>
        <div>
            <label for="password">Passwort:</label>
            <input type="password" id="password" name="mqttpassword" required>
        </div>
        <div>
	    <p>Wichtig: Nutzung nur im oder vor dem Geschäft!</p>
        </div>
        <div>
            <button type="submit">Login</button>
        </div>
    </form>

</body>

</html>
