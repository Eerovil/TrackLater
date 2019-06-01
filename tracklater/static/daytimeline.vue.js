var daytimeline = Vue.component("daytimeline", {
    template: `
    <timeline ref="timeline"
    :items="items"
    :groups="groups"
    :options="options">
    </timeline>
    `,
    props: ["entries", "moduleColors"],
    computed: {
      items() {
        return this.entries.map((entry, i) => {
          let row = {
            id: i,
            group: entry.module,
            start: new Date(entry.start_time),
            content: entry.title,
          }
          if (entry.end_time != undefined) {
              row.end = new Date(entry.end_time);
              if (this.moduleColors[entry.module] != null) {
                  row.style = `background-color: ${this.moduleColors[entry.module]}`
              }
          } else {
              row.type = 'point'
          }
          return row
        })
      },
      groups() {
        ret = []
        for (let module_name in this.moduleColors) {
          ret.push({
            id: module_name,
            content: module_name,
          })
        }
        return ret
      }
    },
    data() {
      let firstDate = new Date(this.entries[0].date_group);
      const day_start = firstDate.setHours(6, 0, 0, 0);
      const day_end = firstDate.setHours(26, 0, 0, 0);

      return {
        options: {
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
        }
      }
    },
});