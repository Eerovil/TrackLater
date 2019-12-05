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
        selection: {
          type: Number,
          default: () => -1
        }
    },
    watch: {
        items(newItems) {
           this.parsedItems.clear();
           this.parsedItems.add(newItems);
           this.timeline.setSelection(this.selection);
        },
        groups(newGroups) {
          this.parsedGroups.clear();
          this.parsedGroups.add(newGroups);
        },
    },
    data() {
      return {
        parsedItems: new vis.DataSet([]),
        parsedGroups: new vis.DataSet([]),
        timeline: null
      }
    },
    mounted() {
        this.parsedItems.add(this.items);
        this.parsedGroups.add(this.groups);
        const container = this.$refs.visualization;
        this.timeline = new vis.Timeline(container, this.parsedItems, this.parsedGroups, this.options);
        this.events.forEach(eventName =>
          this.timeline.on(eventName, props => this.$emit(eventName.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase(), props))
        );
    },
});
