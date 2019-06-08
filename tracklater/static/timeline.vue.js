var vuetimeline = Vue.component("vuetimeline", {
    template: `
    <div ref="visualization"></div>
    `,
    props: {
        groups: {
          type: [Array, DataView],
          default: () => []
        },
        items: {
          type: [Array, DataView],
          default: () => []
        },
        events: {
          type: [Array, DataView],
          default: () => []
        },
        options: {
          type: Object
        },
    },
    watch: {
        items() {
           this.parsedItems.clear();
           this.parsedItems.add(this.items);
        },
        groups() {
          this.parsedGroups.clear();
          this.parsedGroups.add(this.groups);
        }
    },
    data() {
      return {
        parsedItems: new timeline.DataSet([]),
        parsedGroups: new timeline.DataSet([])
      }
    },
    mounted() {
        this.parsedItems.add(this.items);
        this.parsedGroups.add(this.groups);
        const container = this.$refs.visualization;
        this.timeline = new timeline.Timeline(container, this.parsedItems, this.parsedGroups, this.options);
        this.events.forEach(eventName =>
          this.timeline.on(eventName, props => this.$emit(eventName.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase(), props))
        );
    },
});
