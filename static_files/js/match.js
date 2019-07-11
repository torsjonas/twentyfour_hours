$(document).ready(function() {
    var player_1_id = $('#id_player1').val();
    var player_2_id = $('#id_player2').val();

    $('#id_winner option').each(function () {
        if($(this).val() != player_1_id && $(this).val() != player_2_id) {
            $(this).hide();
        }
    });
});