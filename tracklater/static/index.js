$(document).ready(function() {
    $('div#actions').hide();
    listModules();
    getSessions();
    $('#actions .btn_export').on('click', () => {
        if (global_selected) {
            if (global_selected.module_name == $('#modules').val()) {
                updateEntry(
                    global_selected.module_name,
                    global_selected.first_entry,
                    global_selected.first_entry.start_time,
                    global_selected.first_entry.end_time,
                    global_selected.first_entry.project
                )
            } else {
                createEntry();
            }
        }
    });
    $('#actions input.description').on('change', () => {
        // Update project field to match the one specified on the issue
        let issue;
        const title = $('#actions input.description').val();
        for (module_name in issues) {
            for (let i=0; i<issues[module_name].length; i++) {
                if (title.indexOf(issues[module_name][i].title) > -1 &&
                        title.indexOf(issues[module_name][i].key) > -1 ) {
                    issue = issues[module_name][i];
                    break;
                }
            }
        }
        if (issue != undefined && issue.group) {
            for (module_name in projects) {
                for (let i=0; i<projects[module_name].length; i++) {
                    if (projects[module_name][i].group == issue.group) {
                        $('#project').val(projects[module_name][i].id);
                        break;
                    }
                }
            }
        }
    });
    console.log('hello2');
});


function _handleFailure(jqXHR, textStatus, errorThrown) {
    document.open();
    document.write(jqXHR.responseText);
    document.close();
}


var idCounter = 0;

var modules = {};
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
    .fail(_handleFailure)
    .done((data) => {
        console.log(data);
        modules = data;
        for (module_name in modules) {
            $('#modules').append(`<option value="${module_name}">${module_name}</option>`)
        }
    });
}

function getSessions() {
    $.ajax('fetchdata', {
        contentType: 'application/json',
        dataType: 'json'
    })
    .fail(_handleFailure)
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
            if (capabilities[module_name].includes('addentry')) {
                $('#modules').val(module_name);
            }
        }
        updateTable();
    })
    .fail((err) => {
        console.log(err)
    })
}


function refreshEntry(module_name, newEntry) {
    console.log(newEntry)
    for (i in entries[module_name]) {
        let entry = entries[module_name][i];
        if (entry.id == newEntry.id) {
            entry.start_time = parseTime(newEntry.start_time)
            entry.end_time = parseTime(newEntry.end_time)
            entry.title = newEntry.title
            let c = chartItems[entry.date_group]
            c.update(makeRow(module_name, entry))
            break;
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
        entries[module_name].push(entry);
        let c = chartItems[entry.date_group];
        c.add(makeRow(module_name, entry));
    }, 'json')
    .fail(_handleFailure)
}

function updateEntry(module_name, entry, start_time, end_time, project_id) {
    $.post('updateentry', {
        'module': module_name,
        'entry_id': entry.id,
        'start_time': start_time.getTime(),
        'end_time': end_time.getTime(),
        'title': $('#actions input.description').val(),
        'issue_id': entry.issue,
        'project_id': project_id,
        'extra_data': entry.extra_data,
        'text': entry.text,
    }, function(data) {
        refreshEntry(module_name, data);
    }, 'json')
    .fail(_handleFailure)
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
        editable: capabilities[module_name].includes('updateentry'),
    };
    if (entry.end_time != undefined) {
        rowData.end = entry.end_time;
        if (modules[module_name].color != null) {
            rowData.style = `background-color: ${modules[module_name].color}`
        }
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

        let firstDate = new Date(rows.sort((a, b) => {a.start < b.start ? -1 : 1})[0].start.getTime());
        const day_start = firstDate.setHours(6, 0, 0, 0);
        const day_end = firstDate.setHours(26, 0, 0, 0);

        // Configuration for the Timeline
        var options = {
            start: day_start,
            end: day_end,
            editable: true,
            zoomable: false,
            horizontalScroll: true,
            margin: {
                item: 0
            },
            multiselect: true,
            multiselectPerGroup: true,
            snap: null,

            onMove: function(item, callback) {
                if (capabilities[item.group].includes('updateentry')) {
                    let entry = entries[item.group].filter((entry) => entry.idcounter == item.id)[0];
                    
                    updateEntry(
                        item.group, entry, item.start, item.end, entry.project
                    );
                }
                return callback(item);
            },

            onRemove: function(item, callback) {
                if (capabilities[item.group].includes('deleteentry')) {
                    let entry = entries[item.group].filter((entry) => entry.idcounter == item.id)[0];

                    $.post('deleteentry', {
                        'module': item.group,
                        'entry_id': entry.id
                    }, function(data) {
                        console.log("deleted entry " + entry.id + ": " + data);
                    }, 'json')
                    .fail(_handleFailure)
                }
                return callback(item);
            }
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
            let selection = items.get(properties.items[0]);
            let selectionLast = items.get(properties.items[properties.items.length - 1]);

            let module_name = selection.group;
            let first_entry = entries[module_name].filter((entry) => entry.idcounter == selection.id)[0]
            let last_entry = entries[module_name].filter((entry) => entry.idcounter == selectionLast.id)[0]

            global_selected = {module_name, first_entry, last_entry};

            $('div#actions input.description').val(global_selected.first_entry.title);
            $('#project').val(global_selected.first_entry.project);
            $('div#actions').show();
        });
    }

}
