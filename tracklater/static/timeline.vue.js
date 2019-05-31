var timeline = Vue.component("timeline", {
    template: `
    <timeline ref="timeline"
    :items="items"
    :groups="groups"
    :options="options">
    </timeline>
    `,
    props: ["title"],
    data() {
      return {
        groups: [{
            id: 0,
          content: 'Group 1'
        }],
        items: [{
            id: 0,
          group: 0,
          start: new Date(),
          content: 'Item 1'
        }],
        options: {
          editable: true,
        }
      }
    },
});