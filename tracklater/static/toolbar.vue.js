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
    <br>
    <v-combobox
      v-model="entryTitle"
      :items="allIssues"
    >
    </v-combobox>
    </div>
    `,
    props: ["modules"],
    computed: {
        allIssues() {
            let ret = [];
            for (let module_name in this.modules) {
                const _issues = this.modules[module_name].issues || [];
                for (let i=0; i<_issues.length; i++) {
                    ret.push(`${_issues[i].key} ${_issues[i].title}`);
                }
            }
            return ret;
        },
        selectedIssue() {
            for (let module_name in this.modules) {
                const _issues = this.modules[module_name].issues || [];
                for (let i=0; i<_issues.length; i++) {
                    if (`${_issues[i].key} ${_issues[i].title}` === this.entryTitle) {
                        return _issues[i];
                    }
                }
            }
            return null;
        }
    },
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
        return {
            entryTitle: null,
        }
    }
});