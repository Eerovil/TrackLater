var daytimeline = Vue.component("daytimeline", {
    template: `
    <div>
    <vuetimeline ref="timeline"
    :items="items"
    :groups="groups"
    :options="options"
    :events="['select']"
    :selection=selection
    @select="select">
    </vuetimeline>
    </div>
    `,
    props: ["entries"],
    data() {
      return {
        items: [],
      }
    },
    mounted() {
      this.items = this.entriesToItems(this.entries);
    },
    methods: {
      myChangedCallback(arg1, arg2, arg3) {
        console.log(arg1, arg2, arg3)
      },
      select(props) {
        const entry = this.entries[props.items[0]] || null;
        if (entry != null) {
          this.$store.commit('setInput', {title: entry.title, issue: entry.issue || this.findIssue(entry.title)})
          this.$store.commit('setSelectedEntry', entry);
        }
      },
      findIssue(title) {
        return this.$store.getters.findIssue(title)
      },
      onMove: function(item, callback) {
        if (this.modules[item.group].capabilities.includes('updateentry')) {
            let entry = this.entries[item.id];
            if (new Date(entry.start_time).getTimeUTC() === item.start.getTimeUTC() &&
                  new Date(entry.end_time).getTimeUTC() === item.end.getTimeUTC()) {
              return;
            }
            entry.start_time = item.start
            entry.end_time = item.end
            this.$emit('updateEntry', entry)
        }
      },
      onRemove: function(item, callback) {
          if (this.modules[item.group].capabilities.includes('deleteentry')) {
              let entry = this.entries[item.id];
              this.$emit('deleteEntry', entry)
          }
      },
      onAdd: function(item, callback) {
          if (this.modules[item.group].capabilities.includes('addentry')) {
              let timeSnippet = this.generateTimeSnippet(item.start);
              let entry = {
                start_time: timeSnippet.start_time,
                end_time: timeSnippet.end_time,
                title: "Unnamed Entry",
                module: item.group,
                project: ''
              }
              let detectedIssue = this.detectIssue(timeSnippet);
              if (detectedIssue) {
                entry.title = detectedIssue.message;
                entry.project = detectedIssue.project;
              }
              this.$emit('addEntry', entry)
          }
      },
      entriesToItems(entries) {
        return entries.map((entry, i) => {
          let row = {
            id: i,
            group: entry.module,
            start: new Date(entry.start_time),
            className: entry.module,
            content: entry.title,
            title: (entry.text || "").replace(/(?:\r\n|\r|\n)/g, '<br />'),
            editable: {
              updateTime: this.modules[entry.module].capabilities.includes('updateentry'),
              remove: this.modules[entry.module].capabilities.includes('deleteentry')
            },
          }
          let colorObj = this.modules[entry.module].color;
          color = colorObj[entry.group] || colorObj.global;
          if (entry.end_time != undefined) {
              row.end = new Date(entry.end_time);
              if (color != null) {
                  row.style = `background-color: ${color}`
              }
          } else {
              row.type = 'point'
              if (color != null) {
                  row.className += ` point-color-${color}`
              }
          }
          return row
        });
      },
      itemArraysEqual(thisArray, thatArray) {
        if (!thatArray)
            return false;
        if (thisArray.length != thatArray.length)
            return false;

        const keys = [
          'id',
          'group',
          'start',
          'className',
          'content',
          'title',
          'editable',
        ]

        function itemcmp(thisItem, thatItem) {
          if (thisItem instanceof Date) {
            return (thisItem.getTimeUTC() === thatItem.getTimeUTC())
          }
          else if (thisItem instanceof Object) {
            return true; // TODO: If this is ever needed, remember to implement
          }
          else {
            return (thisItem === thatItem)
          }
        }

        for (var i = 0, l=thisArray.length; i < l; i++) {
          for (let key of keys) {
            if (!itemcmp(thisArray[i][key], thatArray[i][key])) {
              return false;
            }
          }
        }
        return true;
      },
      generateTimeSnippet(middle_time) {
        // Go backwards and forwards unit "not much" is happening, and return the 
        // start and end time. If nothing is happening, return an hour.
        const cutoffSeconds = 400;
        let ret = {
          start_time: middle_time.addHours(-0.5),
          end_time: middle_time.addHours(0.5),
        }
        const sorted = this.entries.slice().filter(i => ["thyme", "toggl"].includes(i.module)).sort((a, b) => {
          if (new Date(a.start_time) > new Date(b.start_time)) {
            return 1;
          }
          if (new Date(a.start_time) < new Date(b.start_time)) {
            return -1;
          }
          return 0;
        }).map(i => {
          i.start_time = new Date(i.start_time)
          i.end_time = new Date(i.end_time)
          return i
        })
        // Update ret to fix overlapping issues
        for (el of sorted) {
          if (el.module !== "toggl") {
            continue;
          }
          // If any toggl entry starts or ends between ret times, change ret.
          if (el.start_time < ret.end_time && el.start_time > ret.start_time) {
            ret.end_time = el.start_time;
          }
          if (el.end_time < ret.end_time && el.end_time > ret.start_time) {
            ret.start_time = el.end_time;
          }
        }
        if (ret.start_time >= ret.end_time) {
          return
        }
        console.log('sorted: ', sorted);
        console.log('middle_time: ', middle_time);
        if (sorted.length == 0) {
          return ret;
        }
        // Special case: first thyme entry is after middle_time. Not good
        if (sorted[0].start_time > middle_time) {
          return ret;
        }
        // Special case: last thyme entry is before middle_time. Not good
        if (sorted[sorted.length - 1].end_time < middle_time) {
          return ret;
        }
        // Find the middle thyme entry
        let middleIndex;
        for (let i in sorted) {
          if (sorted[i].end_time > middle_time) {
            middleIndex = i;
            break;
          }
        }
        // Middle item is too far
        if (sorted[middleIndex].start_time.getTime() - middle_time.getTime() > cutoffSeconds * 1000) {
          return ret;
        }
        console.log('middleIndex: ', middleIndex);
        if (!middleIndex) {
          return ret;
        }
        // Go back
        let prevTime = sorted[middleIndex].start_time
        for (let i=middleIndex; i>=0; i--) {
          if (prevTime.getTime() - sorted[i].end_time.getTime() > cutoffSeconds * 1000) {
            ret.start_time = prevTime.addHours(-0.2);
            break;
          }
          if (sorted[i].module == "toggl") {
            // We reached another toggl entry! Return its end_time here for no overlap
            ret.start_time = sorted[i].end_time
            break;
          }
          prevTime = sorted[i].start_time
        }
        // Go forward
        prevTime = sorted[middleIndex].end_time
        for (let i=middleIndex; i<sorted.length; i++) {
          if (sorted[i].start_time.getTime() - prevTime.getTime() > cutoffSeconds * 1000) {
            ret.end_time = prevTime.addHours(0.2);
            break;
          }
          if (sorted[i].module == "toggl") {
            // We reached another toggl entry! Return its start_time here for no overlap
            ret.end_time = sorted[i].start_time
            break;
          }
          prevTime = sorted[i].end_time
        }
        return ret;
      },
      detectIssue(timeSnippet) {
        const entries = this.entries.slice()
          .filter(i => ["gitmodule"]
          .includes(i.module))
          .filter(i => (new Date(i.start_time) < timeSnippet.end_time && new Date(i.start_time) > timeSnippet.start_time))
          .sort((a, b) => {
            if (new Date(a.start_time) > new Date(b.start_time)) {
              return 1;
            }
            if (new Date(a.start_time) < new Date(b.start_time)) {
              return -1;
            }
            return 0;
          })
          .reverse()
        if (entries.length == 0) {
          return null
        }
        let ret = {
          group: entries[0].group
        }
        let issueFound = false;
        entries.forEach(entry => {
          if (issueFound) {
            return;
          }
          // Try to parse issue
          let issueMatch = entry.text.match(/^\w* - ([^ ]+)(.*)/)
          if (issueMatch) {
            let issueSlug = issueMatch[1]
            let issue = this.$store.getters.findIssueByKey(issueSlug);
            if (issue) {
              ret.group = issue.group;
              ret.message = issue.key + " " + issue.title;
              issueFound = true;
            } else {
              ret.message = issueMatch[1] + issueMatch[2];
              ret.group = entry.group;
            }
          }
        });
        ret.project = this.$store.getters.getProjectId(ret.group);
        return ret
      },
    },
    watch: {
      entries(entries, oldEntries) {
        const newItems = this.entriesToItems(entries);
        if (!this.itemArraysEqual(newItems, this.items)) {
          this.items = newItems;
        }
      }
    },
    computed: {
      selection() {
        const selectedEntry = this.$store.state.selectedEntry;
        if (selectedEntry != null && selectedEntry.date_group === (this.entries[0] || {}).date_group) {
          for (let i=0; i<this.entries.length; i++) {
            if (this.entries[i].module == selectedEntry.module &&
                selectedEntry.id != null &&
                this.entries[i].id === selectedEntry.id) {
                  return i;
                }
          }
        }
      },
      modules() {
          return this.$store.state.modules;
      },
      groups() {
        ret = []
        for (let module_name in this.modules) {
          if (this.modules[module_name].capabilities.includes('entries')){
            ret.push({
              id: module_name,
              content: module_name,
            })
          }
        }
        return ret
      },
      options() {
        self = this
        let firstDate = new Date(this.entries[0].date_group);
        const day_start = firstDate.setHours(6, 0, 0, 0);
        const day_end = firstDate.setHours(26, 0, 0, 0);

        return {
          start: day_start,
          end: day_end,
          editable: true,
          zoomable: (screen.width < 960),
          showCurrentTime: false,
          horizontalScroll: false,
          moveable: true,
          margin: {
              item: 0
          },
          snap: null,
          onMove: self.onMove,
          onRemove: self.onRemove,
          onAdd:self.onAdd,
          tooltip: {
            delay: 1
          }
        }
      }
    },
});