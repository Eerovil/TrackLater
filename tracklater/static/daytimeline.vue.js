var daytimeline = Vue.component("daytimeline", {
    template: `
    <timeline ref="timeline"
    :items="items"
    :groups="groups"
    :options="options"
    :events="['select']"
    @select="select">
    </timeline>
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
        const oldEntry = this.$store.state.selectedEntry;
        this.$store.commit('setSelectedEntry', entry);
        if (entry == null) {
          setTimeout(() => {  // Debounce: Only set to null if selectedEntry is unchanged after 100ms
            if (oldEntry == entry) {
              this.$store.commit('setInput', {title: "", issue: null});
            }
          }, 100);
        } else {
          this.$store.commit('setInput', {title: entry.title, issue: entry.issue || this.findIssue(entry.title)})
        }
        this.$emit('selectedEntry', entry);
      },
      findIssue(title) {
        return this.$store.getters.findIssue(title)
      },
      onMove: function(item, callback) {
        if (this.modules[item.group].capabilities.includes('updateentry')) {
            let entry = this.entries[item.id];
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
              let entry = {
                start_time: item.start.addHours(-0.5),
                end_time: item.start.addHours(0.5),
                title: "Unnamed Entry",
                module: item.group,
                project: ''
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
            editable: this.modules[entry.module].capabilities.includes('updateentry'),
          }
          if (entry.end_time != undefined) {
              row.end = new Date(entry.end_time);
              if (this.modules[entry.module].color != null) {
                  row.style = `background-color: ${this.modules[entry.module].color}`
              }
          } else {
              row.type = 'point'
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
      }
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
          zoomable: false,
          horizontalScroll: false,
          margin: {
              item: 0
          },
          multiselect: true,
          multiselectPerGroup: true,
          snap: null,
          onMove: self.onMove,
          onRemove: self.onRemove,
          onAdd:self.onAdd,
        }
      }
    },
});