var home = Vue.component("home", {
    template: `
    <div>
    <toolbar
        :modules="modules"
        v-on:fetchModule=fetchModule($event)
    ></toolbar>
    <daytimeline
      v-for="(groupedEntries, index) in entriesByDategroup"
      :entries="groupedEntries[1]"
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
            // Return an array of 2-arrays, containing [date_group, entry_list]
            let keys = new Set()
            let ret;
            try {
            for (module_name in this.modules) {
                let entries = this.modules[module_name].entries || []
                for (let i=0; i<entries.length; i++) {
                    keys.add(entries[i].date_group)
                }
            }
            // Sort keys to make latest dategroup first
            ret = new Map(Array.from(keys.values(), x => [x, []]).sort((a, b) => a > b ? -1 : 1));
            for (module_name in this.modules) {
                let entries = this.modules[module_name].entries || []
                for (let i=0; i<entries.length; i++) {
                    entries[i].module = module_name
                    let new_entries = ret.get(entries[i].date_group);
                    new_entries.push(entries[i]);
                    ret.set(entries[i].date_group, new_entries);
                }
            }
            } catch (e) {
                console.log(e)
            }
            return Array.from(ret)
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