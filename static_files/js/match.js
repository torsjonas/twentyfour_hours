$(document).ready(function() {

    $("form").submit(function() {
        $("#id_player1").prop("disabled", false);
        $("#id_player2").prop("disabled", false);
    });

    if(window.location.href.indexOf("/change/") > -1) {
        // only filter on the change page
        var player_1_id = $('#id_player1').val();
        var player_2_id = $('#id_player2').val();
        $('#id_winner option').each(function () {
            if($(this).val() != player_1_id && $(this).val() != player_2_id) {
                if($(this).val()) {
                    $(this).remove();
                }
            }
        });

        console.log($("#id_player1").select2('destroy'));
        console.log($("#id_player2").select2('destroy'));
        $("#id_player1").prop('disabled', 'disabled');
        $("#id_player2").prop('disabled', 'disabled');

    }
});