$(document).ready(function() {
    $('div#actions').hide();
    getSessions();
    $('#actions .btn_export').on('click', () => {
        if (global_selected) {
            if (global_selected.type == 'session') {
                exportSession(global_selected.item);
            } else if (global_selected.type == 'entry') {
                updateEntry(global_selected.item.id, global_selected.item.date_group);
            }
        }
    });
    console.log('hello2');
});


var sessions = [];
var timeEntries = [];
var log = [];

var chartItems = {};
var global_selected = null;

function getSessions() {
    $.ajax('sessions', {
        contentType: 'application/json',
        dataType: 'json'
    })
    .done((data) => {
        sessions = [];
        timeEntries = [];
        log = [];
        chartItems = {};
        console.log(data)
        _sessions = data.sessions;
        for (let i=0; i<_sessions.length; i++){
            let session = parseSession(_sessions[i]);
            sessions.push(session);
        }
        _timeEntries = data.time_entries;
        for (let i=0; i<_timeEntries.length; i++){
            let time_entry = parseTimeEntry(_timeEntries[i]);
            timeEntries.push(time_entry);
        }
        _log = data.log;
        for (let i=0; i<_log.length; i++){
            let commit = parseCommit(_log[i]);
            log.push(commit);
        }
        data.issues.forEach(issue => {
            $('#issues').append(`<option>${issue.key} ${issue.summary}</option>`)
        })
        updateTable();
    })
    .fail((err) => {
        console.log(err)
    })
}

function exportSession(session) {
    $.post('export', {
        'start_time': session.start_time.getTime(),
        'end_time': session.end_time.getTime(),
        'name': $('#actions input.description').val(),
    })
    .done((data) => {
        console.log(data);
    })
    .fail((err) => {
        console.log(err);
    })
}

function updateEntry(entryId, date_str) {
    $.post('export', {
        'id': entryId,
        'start_time': new Date(date_str + " " + $('#actions .start_time').val()).getTime(),
        'end_time': new Date(date_str + " " + $('#actions .end_time').val()).getTime(),
        'name': $('#actions input.description').val(),
    })
    .done((data) => {
        console.log(data);
    })
    .fail((err) => {
        console.log(err);
    })
}

function parseTimeEntry(timeEntry) {
    timeEntry.start_time = parseTime(timeEntry.start_time);
    timeEntry.end_time = parseTime(timeEntry.end_time);
    timeEntry.at = parseTime(timeEntry.at);
    return timeEntry;
}

function parseSession(session) {
    session.start_time = parseTime(session.start_time);
    session.end_time = parseTime(session.end_time);
    return session;
}

function parseCommit(commit) {
    commit.time = parseTime(commit.time);
    return commit;
}

function parseTime(time_str) {
    return new Date(time_str);
}

function dateToTimestr(d) {
    hours = format_two_digits(d.getHours());
    minutes = format_two_digits(d.getMinutes());
    seconds = format_two_digits(d.getSeconds());
    return hours + ":" + minutes + ":" + seconds;
}

function format_two_digits(n) {
    return n < 10 ? '0' + n : n;
}
function formatDate(date) {
    return date.toLocaleString('FI');
}

function updateTable() {
    $('#t_data').html('');

    google.charts.load('current', {'packages':['timeline']});
    google.charts.setOnLoadCallback(drawCharts);

    function drawCharts() {
        let dateGroups = new Set();
        sessions.forEach(session => {
            dateGroups.add(session.date_group);
        })
        dateGroups.forEach(dateGroup => {
            drawDayChart(
                sessions.filter(s => s.date_group == dateGroup),
                timeEntries.filter(s => s.date_group == dateGroup),
                log.filter(s => s.date_group == dateGroup),
            )
        })
    }

    function wcmp(a, b) {
        if (a.time < b.time)
          return 1;
        if (a.time > b.time)
          return -1;
        return 0;
    }

    function makeRow(session) {
        return [
            session.date_group, session.category,
            session.windows.sort(wcmp).slice(0, 10).map((w) => w['time'] + "s - " + w['name']).join("<br />"),
            session.start_time, session.end_time,
        ]
    }

    function makeEntryRow(entry) {
        return [
            entry.date_group, 'toggl',
            entry.description,
            entry.start_time, entry.end_time,
        ]
    }

    function makeCommitRow(commit) {
        return [
            commit.date_group, 'commit',
            commit.message + (commit.issue ? "<br />" + commit.issue.summary : ''),
            commit.time, commit.time,
        ]
    }

    function drawDayChart(day_sessions, day_entries, day_log) {
        var container = document.getElementById('timeline');
        var day_container = container.appendChild(document.createElement('div'));
        var chart = new google.visualization.Timeline(day_container);
        var dataTable = new google.visualization.DataTable();

        dataTable.addColumn({ type: 'string', id: 'Session' });
        dataTable.addColumn({ type: 'string', id: 'Type' });
        dataTable.addColumn({ type: 'string', role: 'tooltip', p: {'html': true}});
        dataTable.addColumn({ type: 'datetime', id: 'Start' });
        dataTable.addColumn({ type: 'datetime', id: 'End' });

        let rows = [];
        day_sessions.forEach(session => {
            rows.push(makeRow(session));
        })
        day_entries.forEach(entry => {
            rows.push(makeEntryRow(entry));
        })
        day_log.forEach(commit => {
            rows.push(makeCommitRow(commit));
        })
        dataTable.addRows(rows);

        chartItems[day_sessions[0].date_group] = dataTable;
        
        let today = new Date(day_sessions[0].date_group);
        today.setHours(6);
        let tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);

        google.visualization.events.addListener(chart, 'select', (event) => {
            $('div#actions').hide();
            $('div#actions .toggl_actions').hide();
            $('div#actions input.description').val('');
            let selection = chart.getSelection()[0].row;
            let category = chartItems[day_sessions[0].date_group].getValue(selection, 1)
            let start_time = chartItems[day_sessions[0].date_group].getValue(selection, 3);
            if (category == 'work' || category == 'leisure') {
                let session = sessions.filter((session) => session.start_time == start_time)[0]
                global_selected = {type: 'session', item: session};
                $('div#actions').show();
                $('div#actions input.btn_export').attr('disabled', (session.exported != null));
                if (session.exported){
                    let timeEntry = timeEntries.filter(e => e.id == session.exported)[0];
                    $('div#actions input.description').val(timeEntry.description);
                }
            }
            if (category == 'toggl') {
                let entry = timeEntries.filter((entry) => entry.start_time == start_time)[0];
                global_selected = {type: 'entry', item: entry};
                $('div#actions').show();
                $('div#actions .toggl_actions').show();
                $('div#actions input.btn_export').attr('disabled', false);
                $('div#actions input.description').val(entry.description);
                $('div#actions .toggl_actions input.start_time').val(dateToTimestr(entry.start_time));
                $('div#actions .toggl_actions input.end_time').val(dateToTimestr(entry.end_time));
            }
            console.log(category, start_time);
        });

        chart.draw(dataTable, {
            hAxis: {
                minValue: today,
                maxValue: tomorrow
            },
            tooltip: { isHtml: true }
        });
    }
}

function old_updatetable() {
    for (let key in sessions){
        let session = sessions[key];
        let btn_export = $('<input type="button" value="Export"></input>');
        if (session.exported != null) {
            btn_export.attr('disabled', 'true');
        }
        let row = $(
            `<tr><td><div>
            ${formatDate(session.start_time)} - ${formatDate(session.end_time)} <br />
            ${session.category}
            </div></td></tr>`
        );
        row.find('div').append(btn_export);
        $('#t_data').append(row);
    }
}