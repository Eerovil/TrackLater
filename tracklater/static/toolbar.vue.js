var toolbar = Vue.component("toolbar", {
    template: `
    <div>
    <v-btn
      v-for="(data, module) in modules"
      v-on:click=fetchModule(module)
    >{{ module }}</v-btn>
    </div>
    `,
    props: ["modules"],
    methods: {
        fetchModule(module_name) {
            this.$emit('fetchModule', module_name)
        }
    },
    data() {
        return {}
    }
});