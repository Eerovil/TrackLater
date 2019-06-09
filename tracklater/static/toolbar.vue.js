var toolbar = Vue.component("toolbar", {
    template: `
    <div>
    <v-btn
      v-on:click="fetchAllModules()"
    >Fetch all</v-btn>
    <v-btn
      v-for="(data, module) in modules"
      v-on:click=fetchModule(module)
      :loading="loading[module]"
    >{{ module }}</v-btn>
    <br>
    <v-layout row wrap>
        <v-flex xs4>
            <v-combobox
            v-model="entryTitle"
            :items="allIssues"
            @change="exportEntry"
            >
            </v-combobox>
        </v-flex>
        <v-flex xs4>
            <v-select
            v-model="selectedModule"
            :items="selectableModules"
            @change="exportEntry"
            >
            </v-select>
        </v-flex>
        <v-flex xs4>
            <v-select
            v-model="selectedProject"
            :items="projects"
            :item-text="(item) => item.title"
            :item-value="(item) => item.id"
            @change="exportEntry"
            >
            </v-select>
        </v-flex>
    </v-layout>
    </div>
    `,
    props: [],
    computed: {
        entryTitle: {
            get() {
                return this.$store.state.inputTitle
            },
            set(v) {
                this.$store.commit('setInput', {title: v, issue: this.findIssue(v)});
                if (this.$store.state.inputIssue !== null) {
                    this.selectedProject = (this.getProject(this.$store.state.inputIssue) || {}).id;
                }
            }
        },
        projects() {
            if (this.selectedModule == null) {
                return [];
            }
            return this.modules[this.selectedModule].projects;
        },
        selectedEntry() {
            let entry = this.$store.state.selectedEntry;
            return entry;
        },
        modules() {
            return this.$store.state.modules;
        },
        loading() {
            return this.$store.state.loading;
        },
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
        selectableModules() {
            let ret = [];
            for (let module_name in this.modules) {
                if ((this.modules[module_name].capabilities || []).includes('updateentry')) {
                    ret.push(module_name);
                }
            }
            return ret;
        }
    },
    watch: {
        selectedEntry(entry, oldEntry) {
            this.selectedProject = (entry || {}).project;
            this.selectedModule = (entry || {}).module;
        }
    },
    methods: {
        findIssue(title) {
            return this.$store.getters.findIssue(title)
        },
        fetchModule(module_name) {
            this.$emit('fetchModule', module_name)
        },
        fetchAllModules() {
            for (let module_name in this.modules) {
                this.$emit('fetchModule', module_name)
            }
        },
        getProject(issue) {
            // Get a matching project for issue
            for (const project of this.projects) {
                if (project.group === issue.group) {
                    return project
                }
            }
            return null
        },
        exportEntry() {
            this.$set(this.$store.state.loading, 'export', true);
            this.$emit('exportEntry', Object.assign(this.selectedEntry, {
                issue: this.$store.state.inputIssue,
                title: this.entryTitle,
                module: this.selectedModule,
                project: this.selectedProject
            }));
        }
    },
    data() {
        return {
            selectedModule: null,
            selectedProject: null,
        }
    }
});