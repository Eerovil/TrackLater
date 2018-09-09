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

function refreshEntry(newEntry) {
    console.log(newEntry)
    for (i in timeEntries) {
        let entry = timeEntries[i];
        if (entry.id == newEntry.id) {
            let old_start_time = entry.start_time;
            entry.start_time = parseTime(newEntry.start_time)
            entry.end_time = parseTime(newEntry.end_time)
            entry.description = newEntry.description
            let c = chartItems[entry.date_group]
            for (let row=0; row<c.data.getNumberOfRows(); row++) {
                if (c.data.getValue(row, 3) == old_start_time){
                    c.data.setValue(row, 2, entry.description);
                    c.data.setValue(row, 3, entry.start_time);
                    c.data.setValue(row, 4, entry.end_time);
                    drawChart(c.chart, c.data)
                    break;
                }
            }
        }
    }
}

function createEntry(session, entry) {
    entry = parseTimeEntry(entry);
    entry.date_group = session.date_group;
    timeEntries.push(entry);
    let c = chartItems[entry.date_group];
    c.data.addRow(makeEntryRow(entry));
    drawChart(c.chart, c.data);
}

function exportSession(session) {
    $.post('export', {
        'start_time': session.start_time.getTime(),
        'end_time': session.end_time.getTime(),
        'name': $('#actions input.description').val(),
    }, function(data) {
        createEntry(session, data);
    }, 'json')
}

function updateEntry(entryId, date_str) {
    $.post('export', {
        'id': entryId,
        'start_time': new Date(date_str + " " + $('#actions .start_time').val()).getTime(),
        'end_time': new Date(date_str + " " + $('#actions .end_time').val()).getTime(),
        'name': $('#actions input.description').val(),
    }, function(data) {
        refreshEntry(data);
    }, 'json')
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

function drawChart(chart, dataTable) {
    console.log('drawing chart ', dataTable.getValue(0, 0))
    let today = new Date(dataTable.getValue(0, 0));
    today.setHours(6);
    let tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    chart.draw(dataTable, {
        hAxis: {
            minValue: today,
            maxValue: tomorrow
        },
        tooltip: { isHtml: true }
    });
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

function updateTable() {
    $('#t_data').html('');

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

    google.charts.load('current', {'packages':['timeline']});
    google.charts.setOnLoadCallback(drawCharts);

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

        chartItems[day_sessions[0].date_group] = {chart: chart, data: dataTable};
        
        drawChart(chart, dataTable);

        google.visualization.events.addListener(chart, 'select', (event) => {
            $('div#actions').hide();
            $('div#actions .toggl_actions').hide();
            $('div#actions input.description').val('');
            let selection = chart.getSelection()[0].row;
            let category = chartItems[day_sessions[0].date_group].data.getValue(selection, 1)
            let start_time = chartItems[day_sessions[0].date_group].data.getValue(selection, 3);
            if (category == 'work' || category == 'leisure') {
                let session = sessions.filter((session) => session.start_time == start_time)[0]
                global_selected = {type: 'session', item: session};
                $('div#actions').show();
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