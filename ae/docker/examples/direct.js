function writeDemoCookie() {
  var name = "ct_demo_cookie";
  var value = "ct_demo_value";
  document.cookie = name + "=" + value + "; path=/";
  document.getElementById("status").textContent = "Cookie written: " + document.cookie;
}
writeDemoCookie();
