function ajaxReq(h, a, g, c) {
	var f = j();
	f.open(h, a, true);
	var d = setTimeout(function () {
		f.abort();
		console.log("XHR abort:", h, a);
		f.status = 599;
		f.responseText = "request time-out"
	}, 9000);
	f.onreadystatechange = function () {
		if (f.readyState != 4) {
			return
		}
		clearTimeout(d);
		if (f.status >= 200 && f.status < 300) {
			g(f.responseText)
		}
		else {
			console.log("XHR ERR :", h, a, "->", f.status, f.responseText, f);
			c(f.status, f.responseText)
		}
	};
	try {
		f.send()
	}
	catch (b) {
		console.log("XHR EXC :", h, a, "->", b);
		c(599, b)
	}
}
function dispatchJson(f, d, c) {
	var a;
	try {
		a = JSON.parse(f)
	}
	catch (b) {
		console.log("JSON parse error: " + b + ". In: " + f);
		c(500, "JSON parse error: " + b);
		return
	}
	d(a)
}
function ajaxJson(d, a, c, b) {
	ajaxReq(d, a, function (f) {
		dispatchJson(f, c, b)
	}, b)
}
function ajaxSpin(d, a, c, b) {
	//$("#spinner").removeAttribute("hidden");
	ajaxReq(d, a, function (f) {
		//$("#spinner").setAttribute("hidden", "");
		c(f)
	}, function (f, g) {
		//$("#spinner").setAttribute("hidden", "");
		b(f, g)
	})
}
function ajaxJsonSpin(d, a, c, b) {
	ajaxSpin(d, a, function (f) {
		dispatchJson(f, c, b)
	}, b)
}
function getUrl() {
	consolelog('*** getUrl start ***');
	var port = $('#port').value;
	consolelog('port ' + port);
	let baseurl = document.location.protocol + '//' + document.location.hostname
	return (port == '0' || port == '' || port == 'undefined' || port == null) ? baseurl + ":80/briki" : baseurl + ":"+ port + "/briki"
}
function ajax(url, elem) {
	ajaxReq("GET", url, function (b) {
		//var c = JSON.parse(b);
		var v = b.split(':');
		if (elem != 'undefined' && elem != null && v[1] != 'undefined')
			$("#"+elem).innerHTML = v[1];
	}, function () {
		//console.log("Error")
	});
}
function hide(a) {
	$('#'+a).setAttribute("hidden", "");
}
function showPassword() {
	var a = $('#wifi-passwd'), b = $('#eye');
	if (a.type === "password") {
		a.type = "text";
		addClass(b, 'icon-button-yellow')
	} else {
		a.type = "password";
		removeClass(b, 'icon-button-yellow')
	}
}
function copyip() {
  if (document.selection) { 
	 var range = document.body.createTextRange();
	 range.moveToElementText(document.getElementById('wifi-ip'));
	 range.select().createTextRange();
	 document.execCommand("copy");
  } else if (window.getSelection) {
	 var range = document.createRange();
	 range.selectNode(document.getElementById('wifi-ip'));
	 window.getSelection().addRange(range);
	 document.execCommand("copy");
  }
}

function newKey(){
	document.getElementById("reqRes").innerHTML = "";
	var destination = document.getElementById("destcontrol").value;
	if (destination == "") {
		destination = 'http://172.15.0.5:4000'
	}
	var keyLen = document.getElementById("numcontrol").value;
	if (keyLen == "") {
		keyLen = '128'
	}
	var protocol = document.getElementById("protcontrol").value;

	resp1 = "";
	resp2 = "";
	status1 = 0;
	var xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = function() {
		if (this.readyState == 4) {
			status1 = this.status;
			if(this.status == 200){
				resp1 = this.responseText;

				// retrieve the same key from destination
				var xhttp2 = new XMLHttpRequest();
				xhttp2.onreadystatechange = function() {
					var status2 = this.status;
					if (this.readyState == 4) {
						if(this.status == 200){
							resp2 = this.responseText;
							document.getElementById("reqRes").innerHTML = "Source key: " + resp1 + "<br><br>Destination key:" + resp2;
							if(!resp1.includes('None') && !resp2.includes('None')){
								k1 = resp1.split(",")[0]
								k2 = resp2.split(",")[0]
								if(k1 == k2)
									document.getElementById("reqRes").innerHTML = document.getElementById("reqRes").innerHTML + "<br><br>The two keys are the same.";
								else
									document.getElementById("reqRes").innerHTML = document.getElementById("reqRes").innerHTML + "<br><br>The two keys differ.";
							}
						}
						else
							document.getElementById("reqRes").innerHTML = "Error during request of the same key to destination: " + this.status;
					}
				};
				xhttp2.open("POST", destination + "/startKeyExchange", true);
				xhttp2.send("{'destination' : 'http://172.15.0.4:4000', 'length' : '" + keyLen + "', 'protocol' : '" + protocol +"'}");
			}
			else
				document.getElementById("reqRes").innerHTML = "Error during request: " + this.status;
				
		}
	};
	xhttp.open("POST", "http://172.15.0.4:4000/startKeyExchange", true);
	xhttp.send("{'destination' : '" + destination + "', 'length' : '" + keyLen + "', 'protocol' : '" + protocol +"'}");

	
}

function changeSV(){
	var chunk = document.getElementById("statevectorl").value;
	if (chunk == "")
		chunk = 8;
	var xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = function() {
		if (this.readyState == 4 && this.status == 200) {
		document.getElementById("reqRes").innerHTML = this.responseText;
		}
	};
	xhttp.open("POST", "http://172.15.0.4:4000/settings", true);
	xhttp.send("{'chunk': " + chunk + "}");
}


function changeAuth(){
	var authMethod = document.getElementById("auth").value;
	// translate strings in correct parameter name
	if(authMethod == 'SPHINCS+')
		authMethod = 'sphincs+';
	else
		authMethod = 'aesgcm';

	var xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = function() {
		if (this.readyState == 4) {
			status1 = this.status;
			if(this.status == 200){
				resp1 = this.responseText;

				// retrieve the same key from destination
				var xhttp2 = new XMLHttpRequest();
				xhttp2.onreadystatechange = function() {
					var status2 = this.status;
					if (this.readyState == 4) {
						if(this.status == 200){
							resp2 = this.responseText;
							document.getElementById("reqRes").innerHTML = resp1;
						}
						else
							document.getElementById("reqRes").innerHTML = "Error during request: " + this.status;
					}
				};
				xhttp2.open("POST", "http://172.15.0.5:4000/settings", true);
				xhttp2.send("{'auth' : '" + authMethod + "'}");
			}
			else
				document.getElementById("reqRes").innerHTML = "Error during request: " + this.status;
		}
	};
	xhttp.open("POST", "http://172.15.0.4:4000/settings", true);
	xhttp.send("{'auth' : '" + authMethod + "'}");
}

function chSettings(){
	var irCheck = document.getElementById("IRcheck").checked;
	var mitmCheck = document.getElementById("MITMcheck").checked;
	var attack = ""
	if(irCheck == true)
		attack = "interceptAndResend=1"
	else
		attack = "interceptAndResend=0"
	if(mitmCheck == true)
		attack = attack + "&manInTheMiddle=1"
	else
		attack = attack + "&manInTheMiddle=0"
	var xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = function() {
		if (this.readyState == 4 && this.status == 200) {
		document.getElementById("reqRes").innerHTML = this.responseText;
		}
	};
	xhttp.open("POST", "http://172.15.0.6:4000/attacks?" + attack, true);
	xhttp.send();

}


function clearResult(){
	document.getElementById("reqRes").innerHTML = "";
}

