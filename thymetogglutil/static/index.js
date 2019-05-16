$(document).ready(function() {
    $('div#actions').hide();
    getSessions();
    $('#actions .btn_export').on('click', () => {
        if (global_selected) {
            if (global_selected.type == 'session') {
                exportSession(global_selected.item, global_selected_last.item.end_time);
            } else if (global_selected.type == 'entry') {
                updateEntry(global_selected.item.id, global_selected.item.date_group);
            }
        }
    });
    $('#actions input.description').on('change', () => {
        // Update project field to match the one specified on the issue
        issue = issues.filter((issue) => {
            return ($('#actions input.description').val().indexOf(issue.key) > -1);
        });
        if (issues.length > 0 && issue[0] !== undefined && issue[0].project) {
            $('#project').val(issue[0].project);
        }
    });
    console.log('hello2');
});


var sessions = [];
var timeEntries = [];
var idCounter = 0;
var log = [];
var projects = [];
var issues = [];

var entries = {};
var issues = {};
var projects = {};

var chartItems = {};
var global_selected = null;
var global_selected_last = null;

function getSessions() {
    $.ajax('fetchdata', {
        contentType: 'application/json',
        dataType: 'json'
    })
    .done((data) => {
        console.log(data)
        for (module_name in data) {
            projects[module_name] = data[module_name].projects;
            projects[module_name].forEach(project => {
                $('#project').append(`<option value="${project.id}">${project.title}</option>`)
            });
            entries[module_name] = []
            for (let i=0; i<data[module_name].entries.length; i++) {
                let entry = data[module_name].entries[i];
                entry.start_time = parseTime(entry.start_time);
                entry.end_time = parseTime(entry.end_time);
                entry.idcounter = idCounter++;
                entries[module_name].push(entry);
            }
            issues[module_name] = data[module_name].issues;
            issues[module_name].forEach(issue => {
                $('#issues').append(`<option value="${issue.key}">${issue.key} ${issue.title}"></option>`)
            });
        }
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

function exportSession(session, end_time) {
    $.post('export', {
        'start_time': session.start_time.getTime(),
        'end_time': end_time.getTime(),
        'name': $('#actions input.description').val(),
        'project': $('#project').val(),
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
        'project': $('#project').val(),
    }, function(data) {
        refreshEntry(data);
    }, 'json')
}

function deleteEntry(entryId) {
    $.post('delete', {
        'id': entryId
    }, function(data) {
        alert("deleted entry " + entryId + ": " + data);
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

function parseSlack(message) {
    message.time = parseTime(message.time);
    return message;
}

function parseTime(time_str) {
    if (time_str == null) {
        return time_str;
    }
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

function updateTable() {

    let dateGroups = new Set();
    for (module_name in entries) {
        entries[module_name].forEach(entry => {
            dateGroups.add(entry.date_group)
        })
    }
    Array.from(dateGroups).sort().forEach(date_group => {
        let filteredEntries = {};
        for (module_name in entries) {
            filteredEntries[module_name] = entries[module_name].filter(s => s.date_group == date_group)
        }
        drawDayChart(date_group, filteredEntries);
    })

    function drawDayChart(date_group, filteredEntries) {
        var container = document.getElementById('timeline');
        var day_container = container.appendChild(document.createElement('div'));

        let rows = [];

        for (module_name in filteredEntries) {
            for (let i=0; i<filteredEntries[module_name].length; i++) {
                const entry = filteredEntries[module_name][i];
                let rowData = {
                    id: entry.idcounter,
                    start: entry.start_time,
                    group: module_name,
                    className: module_name,
                    content: entry.title,
                    title: entry.text.join("<br />"),
                    editable: false,
                };
                if (entry.end_time != undefined) {
                    rowData.end = entry.end_time;
                } else {
                    rowData.type = 'point'
                }
                rows.push(rowData);
            }
        }
        var items = new vis.DataSet(rows);
        chartItems[date_group] = items;

        // Configuration for the Timeline
        var options = {
            editable: true,
            zoomable: false,
            horizontalScroll: true,
            margin: {
                item: 0
            },
            multiselect: true,
            multiselectPerGroup: true,
            snap: null,

            // onMove: function(item, callback) {
            //     if (item.group == ) {
            //         let entry = timeEntries.filter((entry) => entry.idcounter == item.id)[0];
                    
            //         $.post('export', {
            //             'id': entry.id,
            //             'start_time': item.start.getTime(),
            //             'end_time': item.end.getTime(),
            //             'name': $('#actions input.description').val(),
            //         }, function(data) {
            //             refreshEntry(data);
            //         }, 'json')
            //     }
            //     return callback(item);
            // },

            // onRemove: function(item, callback) {
            //     if (item.group == 'entry') {
            //         let entry = timeEntries.filter((entry) => entry.idcounter == item.id)[0];
                    
            //         deleteEntry(entry.id);
            //     }
            //     return callback(item);
            // }
        };

        var groups = []
        for (module_name in filteredEntries) {
            groups.push({
                id: module_name,
                content: module_name,
                className: module_name + '-group',
            })
        }
    
        // Create a Timeline
        var timeline = new vis.Timeline(day_container, items, options, groups);
        timeline.on('select', (properties) => {
            $('div#actions').hide();
            $('div#actions .toggl_actions').hide();
            $('div#actions input.description').val('');
            let selection = items.get(properties.items[0]);
            let selectionLast = items.get(properties.items[properties.items.length - 1]);
            let category = selection.group;
            if (category == 'session') {
                let session = sessions.filter((session) => session.idcounter == selection.id)[0]
                let sessionLast = sessions.filter((session) => session.idcounter == selectionLast.id)[0]
                global_selected = {type: 'session', item: session};
                global_selected_last = {type: 'session', item: sessionLast};
                $('div#actions').show();
                if (session.exported){
                    let timeEntry = timeEntries.filter(e => e.id == session.exported)[0];
                    $('div#actions input.description').val(timeEntry.description);
                    $('#project').val(timeEntry.project);
                }
            }
            if (category == 'entry') {
                let entry = timeEntries.filter((entry) => entry.idcounter == selection.id)[0];
                global_selected = {type: 'entry', item: entry};
                $('div#actions').show();
                $('div#actions .toggl_actions').show();
                $('div#actions input.btn_export').attr('disabled', false);
                $('div#actions input.description').val(entry.description);
                $('#project').val(entry.project);
                $('div#actions .toggl_actions input.start_time').val(dateToTimestr(entry.start_time));
                $('div#actions .toggl_actions input.end_time').val(dateToTimestr(entry.end_time));
            }
        });
    }

}
