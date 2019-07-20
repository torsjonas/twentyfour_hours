function formatScore(x) {
    return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function popitup(url) {
    newwindow=window.open(url,'name','height=500,width=1000');
    if (window.focus) {newwindow.focus()}
    return false;
}

function formatDate(date) {
    var monthNames = [
      "January", "February", "March",
      "April", "May", "June", "July",
      "August", "September", "October",
      "November", "December"
    ];

    var day = date.getDate();
    var monthIndex = date.getMonth();
    var year = date.getFullYear();

    return day + ' ' + monthNames[monthIndex] + ' ' + year;
}

function numberWithSpaces(x) {
    return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

function showScoreGraph (data) {
    if (!data || data.length === 0) {
        return;
    }

    var game = data[0].game;
    var seriesData = data.map(i => [new Date(i.date).getTime(), i.score]);
    var playerLookup = data.reduce((ret, item) => {
        ret[new Date(item.date).getTime() + '-' + item.score] = item.playerInitials
        return ret;
    }, {});
    var config = {
        chart: {
            type: 'scatter',
            zoomType: 'xy'
        },
        title: {text: 'Scores'},
        plotOptions: {
            scatter: {
                marker: {
                    radius: 5,
                    states: {
                        hover: {
                            enabled: true,
                            lineColor: 'rgb(100,100,100)'
                        }
                    }
                },
                states: {
                    hover: {
                        marker: {
                            enabled: false
                        }
                    }
                }
            }
        },
        tooltip: {
            formatter: function () {
                return 'Score: <b>' + numberWithSpaces(this.y) + '</b><br/>' +
                    'Date: <b>' + formatDate(new Date(this.x)) + '</b><br/>' +
                    'Player: <b>' + playerLookup[this.x + '-' + this.y] + '</b>';
            }
        },
        xAxis: {
            type: 'datetime'
        },
        yAxis: {
            title: {
                text: 'Score'
            }
        },
        series: [
            {
                name: game,
                data: seriesData
            }
        ]
    };

    Highcharts.chart('modalScoreGraphContainer', config);
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

$('#modalScoreGraph').on('show.bs.modal', function (event) {
    var button = $(event.relatedTarget);
    var gameId = button.data('game-id');
    if (!fetch || !gameId) {
        return;
    }

    fetch('/data/game-score/?game=' + gameId)
        .then(response => response.json())
        .then(body => {
            showScoreGraph(body.data);
        });
});
});