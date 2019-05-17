$(document).ready(function() {
    $('div#actions').hide();
    listModules();
    getSessions();
    $('#actions .btn_export').on('click', () => {
        if (global_selected) {
            createEntry();
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


var idCounter = 0;

var modules = [];
var entries = {};
var issues = {};
var projects = {};
var capabilities = {};

var chartItems = {};
var global_selected = null;

function listModules() {
    $.ajax('listmodules', {
        contentType: 'application/json',
        dataType: 'json'
    })
    .done((data) => {
        console.log(data);
        modules = data;
        modules.forEach(module => {
            $('#modules').append(`<option value="${module}">${module}</option>`)
        });
    });
}

function getSessions() {
    $.ajax('fetchdata', {
        contentType: 'application/json',
        dataType: 'json'
    })
    .done((data) => {
        console.log(data)
        for (module_name in data) {
            capabilities[module_name] = data[module_name].capabilities;
            if (capabilities[module_name].includes('projects')) {
                projects[module_name] = data[module_name].projects;
                projects[module_name].forEach(project => {
                    $('#project').append(`<option value="${project.id}">${project.title}</option>`)
                });
            }
            if (capabilities[module_name].includes('entries')) {
                entries[module_name] = []
                for (let i=0; i<data[module_name].entries.length; i++) {
                    let entry = data[module_name].entries[i];
                    entry.start_time = parseTime(entry.start_time);
                    entry.end_time = parseTime(entry.end_time);
                    entry.idcounter = idCounter++;
                    entries[module_name].push(entry);
                }
            }
            if (capabilities[module_name].includes('issues')) {
                issues[module_name] = data[module_name].issues;
                issues[module_name].forEach(issue => {
                    $('#issues').append(`<option value="${issue.key} ${issue.title}"></option>`)
                });
            }
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

function createEntry() {
    const first_entry = global_selected.first_entry;
    const last_entry = global_selected.last_entry;
    const module_name = $('#modules').val();
    const entry_module = global_selected.module_name;
    $.post('updateentry', {
        'module': module_name,
        'start_time': first_entry.start_time.getTime(),
        'end_time': last_entry.end_time.getTime(),
        'title': $('#actions input.description').val(),
        'project_id': $('#project').val(),
    }, function(data) {
        console.log(data);
        let entry = data;
        entry.start_time = parseTime(entry.start_time);
        entry.end_time = parseTime(entry.end_time);
        entry.idcounter = idCounter++;
        entries[entry_module].push(entry);
        let c = chartItems[entry.date_group];
        c.add(makeRow(module_name, entry));
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

function makeRow(module_name, entry) {
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
    return rowData;
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
                rows.push(makeRow(module_name, entry));
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

            let module_name = selection.group;
            let first_entry = entries[module_name].filter((entry) => entry.idcounter == selection.id)[0]
            let last_entry = entries[module_name].filter((entry) => entry.idcounter == selectionLast.id)[0]

            global_selected = {module_name, first_entry, last_entry};

            $('div#actions').show();
        });
    }

}
