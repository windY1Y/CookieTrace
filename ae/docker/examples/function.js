function getCookieValue() {
  return "ct_demo_value";
}
function writeDemoCookie() {
  var name = "ct_demo_cookie";
  var value = getCookieValue();
  document.cookie = name + "=" + value + "; path=/";
  document.getElementById("status").textContent = "Cookie written: " + document.cookie;
}
writeDemoCookie();
