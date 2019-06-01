var home = Vue.component("home", {
    template: `
    <div>
    <toolbar
        :modules="modules"
        v-on:fetchModule=fetchModule($event)
    ></toolbar>
    <daytimeline
      v-for="(entries, dateGroup) in entriesByDategroup"
      :entries="entries"
      :modules="modules"
      @addEntry="updateEntry"
      @updateEntry="updateEntry"
      @deleteEntry="deleteEntry"
    ></daytimeline>
    </div>
    `,
    data() {
        return {
            modules: {}
        }
    },
    computed: {
        entriesByDategroup() {
            let ret = {}
            try {
            for (module_name in this.modules) {
                let entries = this.modules[module_name].entries || []
                for (let i=0; i<entries.length; i++) {
                    if (ret[entries[i].date_group] == undefined) {
                        ret[entries[i].date_group] = []
                    }
                    entries[i].module = module_name
                    ret[entries[i].date_group].push(entries[i])
                }
            }
            } catch (e) {
                console.log(e)
            }
            return ret
        }
    },
    methods: {
        fetchModule(module_name) {
            console.log(`Fetching ${module_name}`)
            this.$set(this.modules[module_name], 'loading', true) 

            axios.get("fetchdata", {params: {keys: [module_name]}}).then(response => {
                console.log(response)
                this.modules = Object.assign(this.modules, response.data)
                this.$set(this.modules[module_name], 'loading', false)
            })
        },
        updateEntry(entry) {
            axios.post("updateentry", {
                'module': entry.module,
                'entry_id': entry.id,
                'start_time': entry.start_time.getTimeUTC(),
                'end_time': entry.end_time.getTimeUTC(),
                'title': "Placeholder",
                'issue_id': entry.issue,
                'project_id': "0",
                'extra_data': entry.extra_data,
                'text': entry.text,
            }).then(response => {
                console.log(response)
                updated_entries = this.modules[entry.module].entries.filter((_entry) => _entry.id !== entry.id);
                updated_entries.push(response.data)
                this.$set(this.modules[entry.module], 'entries', updated_entries);
            }).catch(_handleFailure)
        },
        deleteEntry(entry) {
            axios.post('deleteentry', {
                'module': entry.module,
                'entry_id': entry.id
            }).then((response) => {
                console.log("deleted entry " + entry.id + ": " + response.data);
                updated_entries = this.modules[entry.module].entries.filter((_entry) => _entry.id !== entry.id);
                this.$set(this.modules[entry.module], 'entries', updated_entries);
            }).catch(_handleFailure)
        }

    },
    mounted() {
        axios.get("listmodules").then(response => {
            console.log(response)
            this.modules = response.data
        })
    }
});