var home = Vue.component("home", {
    template: `
    <div>
    <toolbar
        v-on:fetchModule=fetchModule($event)
        v-on:exportEntry=updateEntry($event)
    ></toolbar>
    <daytimeline
      v-for="(groupedEntries, index) in entriesByDategroup"
      :entries="groupedEntries[1]"
      @addEntry="updateEntry"
      @updateEntry="updateEntry"
      @deleteEntry="deleteEntry"
    ></daytimeline>
    </div>
    `,
    data() {
        return {}
    },
    computed: {
        modules() {
            return this.$store.state.modules;
        },
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
            this.$store.commit('setLoading', {module_name, loading: true});

            axios.get("fetchdata", {params: {keys: [module_name]}}).then(response => {
                console.log(response)
                this.$store.commit('setModules', Object.assign(this.modules, response.data));
                this.$store.commit('setLoading', {module_name, loading: false});
            })
        },
        parseTime(time) {
            if (typeof time === "string") {
                return new Date(time)
            }
            return time
        },
        updateEntry(entry) {
            axios.post("updateentry", {
                'module': entry.module,
                'entry_id': entry.id,
                'start_time': this.parseTime(entry.start_time).getTimeUTC(),
                'end_time': this.parseTime(entry.end_time).getTimeUTC(),
                'title': entry.title || "Placeholder",
                'issue_id': entry.issue,
                'project_id': "0",
                'extra_data': entry.extra_data,
                'text': entry.text,
            }).then(response => {
                console.log(response)
                updated_entries = this.$store.state.modules[entry.module].entries.filter((_entry) => _entry.id !== entry.id);
                updated_entries.push(response.data)
                this.$store.commit('setEntries', {module_name: entry.module, entries: updated_entries});
                this.$set(this.$store.state.loading, 'export', false);
            }).catch(_handleFailure)
        },
        deleteEntry(entry) {
            axios.post('deleteentry', {
                'module': entry.module,
                'entry_id': entry.id
            }).then((response) => {
                console.log("deleted entry " + entry.id + ": " + response.data);
                updated_entries = this.$store.state.modules[entry.module].entries.filter((_entry) => _entry.id !== entry.id);
                this.$store.commit('setEntries', {module_name: entry.module, entries: updated_entries});
            }).catch(_handleFailure)
        }

    },
    mounted() {
        axios.get("listmodules").then(response => {
            console.log(response)
            this.$store.commit('setModules', response.data);
        })
    }
});