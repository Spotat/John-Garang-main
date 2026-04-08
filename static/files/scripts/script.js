function openNav() {
    document.getElementById("sideNav").style.width = "90%"
    document.getElementById("sideNav").style.visibility = "visible"
    document.getElementById("sideNav").style.opacity = "1"
    document.getElementById("sideNav").style.zIndex = "99"
}
function closeNav() {
    document.getElementById("sideNav").style.width = "0%"
    document.getElementById("sideNav").style.visibility = "hidden"
    document.getElementById("sideNav").style.opacity = "0"
    document.getElementById("sideNav").style.zIndex = "-99"
}