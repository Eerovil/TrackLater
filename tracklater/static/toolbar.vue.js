var toolbar = Vue.component("toolbar", {
    template: `
    <div>
    <v-btn
      v-on:click="fetchAllModules()"
    >Fetch all</v-btn>
    <v-btn
      v-for="(data, module) in modules"
      v-on:click=fetchModule(module)
      :loading="modules[module].loading"
    >{{ module }}</v-btn>
    </div>
    `,
    props: ["modules"],
    methods: {
        fetchModule(module_name) {
            this.$emit('fetchModule', module_name)
        },
        fetchAllModules() {
            for (let module_name in this.modules) {
                this.$emit('fetchModule', module_name)
            }
        }
    },
    data() {
        return {}
    }
});