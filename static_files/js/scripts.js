function formatScore(x) {
    return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function popitup(url) {
    newwindow=window.open(url,'name','height=500,width=1000');
    if (window.focus) {newwindow.focus()}
    return false;
}

$(document).ready(function() {

$("select").each(function(){
    $(this).select2({});
});

$('#score_form').on('submit', function(e) {
    var game = $("#id_game option:selected" ).text();
    var score = $('#id_score').val().replace(/\D/g, "");
    var player = $("#id_player option:selected" ).text();
    if(score && game && player) {
        var text = LANG_ARE_YOU_SURE_YOU_WANT_TO_SUBMIT_THE_FOLLOWING_SCORE + "\n";
        text += LANG_GAME + ": " + game + "\n";
        text += LANG_SCORE + ": " + formatScore(score) + "\n";
        text += LANG_PLAYER + ": " + player + "\n";
        if(!confirm(text)) {
            e.preventDefault();
        }
    }
});

$(".set-winner-link").click(function(e){
    e.preventDefault();
    popitup($(this).data("url"));
});

});