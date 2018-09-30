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
    $('#actions .btn_split').on('click', () => {
        if (global_selected) {
            if (global_selected.type == 'entry') {
                splitEntry(global_selected.item.id, global_selected.item.date_group);
            }
        }
    });
    console.log('hello2');
});


var sessions = [];
var timeEntries = [];
var idCounter = 0;
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
            session.idcounter = idCounter++;
            sessions.push(session);
        }
        _timeEntries = data.time_entries;
        for (let i=0; i<_timeEntries.length; i++){
            let time_entry = parseTimeEntry(_timeEntries[i]);
            time_entry.idcounter = idCounter++;
            timeEntries.push(time_entry);
        }
        _log = data.log;
        for (let i=0; i<_log.length; i++){
            let commit = parseCommit(_log[i]);
            commit.idcounter = idCounter++;
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
            entry.start_time = parseTime(newEntry.start_time)
            entry.end_time = parseTime(newEntry.end_time)
            entry.description = newEntry.description
            let c = chartItems[entry.date_group]
            c.update({id: entry.idcounter,
                title: entry.description,
                content: entry.description,
                start: entry.start_time,
                end: entry.end_time,
            })
        }
    }
}

function createEntry(session, entry) {
    entry = parseTimeEntry(entry);
    entry.date_group = session.date_group;
    entry.idcounter = idCounter++;
    timeEntries.push(entry);
    let c = chartItems[entry.date_group];
    c.add(makeRow(entry, 'entry'));
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

function splitEntry(entryId, date_str) {
    $.post('split', {
        'id': entryId,
        'start_time': new Date(date_str + " " + $('#actions .start_time').val()).getTime(),
        'end_time': new Date(date_str + " " + $('#actions .end_time').val()).getTime(),
        'split_time': new Date(date_str + " " + $('#actions .split_time').val()).getTime(),
        'name': $('#actions input.description').val(),
    }, function(data) {
        refreshEntry(data.entry1);
        createEntry({date_group: date_str}, data.entry2);
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

function makeRow(obj, type) {
    switch (type) {
        case 'session':
        return {
                id: obj.idcounter,
                content: '',
                start: obj.start_time,
                end: obj.end_time,
                group: 'session',
                className: 'session-' + obj.category,
                title: obj.windows.sort(wcmp).slice(0, 10).map((w) => w['time'] + "s - " + w['name']).join("<br />"),
        }
        case 'entry':
        return {
                id: obj.idcounter,
                content: obj.description,
                start: obj.start_time,
                end: obj.end_time,
                group: 'entry',
                className: 'entry',
                title: obj.description,
        }
        case 'commit':
        return {
                id: obj.idcounter,
                content: '',
                start: obj.time,
                group: 'commit',
                className: 'commit',
                title: obj.message + (obj.issue ? "<br />" + obj.issue.key + " " + obj.issue.summary : ''),
                type: 'point',
        }
    }
}

function updateTable() {

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


    function drawDayChart(day_sessions, day_entries, day_log) {
        var container = document.getElementById('timeline');
        var day_container = container.appendChild(document.createElement('div'));

        let rows = [];
        day_sessions.forEach(session => {
            rows.push(makeRow(session, 'session'));
        })
        day_entries.forEach(entry => {
            rows.push(makeRow(entry, 'entry'));
        })
        day_log.forEach(commit => {
            rows.push(makeRow(commit, 'commit'));
        })
        var items = new vis.DataSet(rows);
        chartItems[day_sessions[0].date_group] = items;

        // Configuration for the Timeline
        var options = {
            zoomable: false,
            horizontalScroll: true,
            margin: {
                item: 0
            }
        };

        var groups = [
            {
                id: 'entry',
                content: 'entry',
                className: 'entry-group',
            },
            {
                id: 'session',
                content: 'session',
                className: 'session-group',
            },
            {
                id: 'commit',
                content: 'commit',
                className: 'commit-group',
            }
        ]
    
        // Create a Timeline
        var timeline = new vis.Timeline(day_container, items, options, groups);
        timeline.on('select', (properties) => {
            $('div#actions').hide();
            $('div#actions .toggl_actions').hide();
            $('div#actions input.description').val('');
            let selection = items.get(properties.items[0]);
            let category = selection.group;
            if (category == 'session') {
                let session = sessions.filter((session) => session.idcounter == selection.id)[0]
                global_selected = {type: 'session', item: session};
                $('div#actions').show();
                if (session.exported){
                    let timeEntry = timeEntries.filter(e => e.id == session.exported)[0];
                    $('div#actions input.description').val(timeEntry.description);
                }
            }
            if (category == 'entry') {
                let entry = timeEntries.filter((entry) => entry.idcounter == selection.id)[0];
                global_selected = {type: 'entry', item: entry};
                $('div#actions').show();
                $('div#actions .toggl_actions').show();
                $('div#actions input.btn_export').attr('disabled', false);
                $('div#actions input.description').val(entry.description);
                $('div#actions .toggl_actions input.start_time').val(dateToTimestr(entry.start_time));
                $('div#actions .toggl_actions input.end_time').val(dateToTimestr(entry.end_time));
                $('div#actions .toggl_actions input.split_time').val(dateToTimestr(entry.start_time));
            }
        });
    }

}
