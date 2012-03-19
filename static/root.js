(function () {
    var oldScroll = window.pageYOffset;
    window.addEventListener("scroll", function () {
        if (window.pageYOffset > oldScroll) {
            document.body.style.height = document.body.clientHeight + "px";
        } else {
            if (window.pageYOffset > 0) {
                document.body.style.height = Math.max(window.pageYOffset +  window.innerHeight,
                        document.getElementById("sagecell_pageContent").clientHeight) + "px";
            } else {
                document.body.style.height = "";
            }
        }
        oldScroll = window.pageYOffset;
    });
}());
