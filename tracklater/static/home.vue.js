var home = Vue.component("home", {
    template: `
    <div>
    <toolbar
        class="toolbar"
        v-on:fetchModule=fetchModule($event)
        v-on:exportEntry=updateEntry($event)
        v-on:setToolbarHeight=setToolbarHeight($event)
        v-bind:style="{ height: toolbarHeight }"
    ></toolbar>
    <div
        class="toolbar-separator"
        v-bind:style="{ height: toolbarSepHeight }"
    ></div>
    <daytimeline
      v-for="dateGroupData in entriesByDategroup"
      ref="daytimelines"
      :entries="dateGroupData.entries"
      :key="dateGroupData.dateGroup"
      @addEntry="updateEntry"
      @updateEntry="updateEntry"
      @deleteEntry="deleteEntry"
    ></daytimeline>
    </div>
    `,
    data() {
        return {
            toolbarHeight: '110px',
            toolbarSepHeight: '110px',
        }
    },
    computed: {
        modules() {
            return this.$store.state.modules;
        },
        entriesByDategroup() {
            // Return an array of objects, containing {dateGroup, entries}
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
            ret = []
            for (dateGroup of Array.from(keys.values()).sort((a, b) => a > b ? -1 : 1)) {
                ret.push({dateGroup, entries: []});
            }
            for (module_name in this.modules) {
                let entries = this.modules[module_name].entries || []
                for (let i=0; i<entries.length; i++) {
                    entries[i].module = module_name
                    const index = ret.findIndex((item) => item.dateGroup === entries[i].date_group);
                    ret[index].entries.push(entries[i]);
                }
            }
            } catch (e) {
                console.log(e)
            }
            return ret;
        },
        debounceUpdateWeek() {
            return _.debounce(this.updateWeek, 500)
        }
    },
    methods: {
        fetchModule(module_name, parse) {
            if (parse == undefined) {
                parse = 1;
            }
            console.log(`Fetching ${module_name}`)
            this.$store.commit('setLoading', {module_name, loading: true});

            axios.get("fetchdata", {params: {
                    parse: parse,
                    keys: [module_name],
                    from: this.$store.getters.getFrom,
                    to: this.$store.getters.getTo,
                }}).then(response => {
                console.log(response)
                this.$store.commit('updateModules', response.data);
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
            this.$store.commit('setLoading', {module_name: 'updateentry', loading: true});
            updated_entries = this.$store.state.modules[entry.module].entries.filter((_entry) => _entry.id !== entry.id);
            let placeholderid;
            if (!entry.id) {
                placeholderid = "placeholderid" + Math.random();
            }
            updated_entries.push({
                id: entry.id || placeholderid,
                start_time: this.parseTime(entry.start_time),
                end_time: this.parseTime(entry.end_time),
                title: entry.title || "Placeholder",
                module: entry.module,
                date_group: this.parseTime(entry.start_time).toISOString().split('T')[0],
            })
            this.$store.commit('setEntries', {module_name: entry.module, entries: updated_entries});
            axios.post("updateentry", {
                'module': entry.module,
                'entry_id': entry.id,
                'start_time': this.parseTime(entry.start_time).getTimeUTC(),
                'end_time': this.parseTime(entry.end_time).getTimeUTC(),
                'title': entry.title || "Placeholder",
                'issue_id': (entry.issue || {}).id,
                'project_id': entry.project || "0",
                'extra_data': entry.extra_data,
                'text': entry.text,
            }).then(response => {
                console.log(response)
                updated_entries = this.$store.state.modules[entry.module].entries.filter((_entry) => _entry.id !== entry.id && _entry.id !== placeholderid);
                updated_entries.push(response.data)
                this.$store.commit('setInput', {title: response.data.title, issue: null})
                this.$store.commit('setEntries', {module_name: entry.module, entries: updated_entries});
                this.$store.commit('setLoading', {module_name: 'updateentry', loading: false});
            }).catch(_handleFailure)
        },
        deleteEntry(entry) {
            this.$store.commit('setLoading', {module_name: 'deleteentry', loading: true});
            updated_entries = this.$store.state.modules[entry.module].entries.filter((_entry) => _entry.id !== entry.id);
            this.$store.commit('setEntries', {module_name: entry.module, entries: updated_entries});
            this.$store.commit('setSelectedEntry', null)
            axios.post('deleteentry', {
                'module': entry.module,
                'entry_id': entry.id
            }).then((response) => {
                console.log("deleted entry " + entry.id + ": " + response.data);
                updated_entries = this.$store.state.modules[entry.module].entries.filter((_entry) => _entry.id !== entry.id);
                this.$store.commit('setInput', {title: null, issue: null})
                this.$store.commit('setEntries', {module_name: entry.module, entries: updated_entries});
                this.$store.commit('setLoading', {module_name: 'deleteentry', loading: false});
            }).catch(_handleFailure)
        },
        setToolbarHeight(event) {
            this.toolbarHeight = `${event.height}px`;
            if (event.separator) {
                this.toolbarSepHeight = `${event.height}px`;
            }
        },
        updateWeek() {
            for (el of this.$refs.daytimelines) {
                el.$refs.timeline.unloadTimeline();
            }
            this.$store.commit('setSelectedEntry', null)
            this.$store.commit('setInput', {title: null, issue: null})
            this.fetchModule("all", 0)
        },
    },
    watch: {
        "$store.state.currentWeek"() {
            if (!this.$refs.daytimelines) {
                return;
            }
            this.debounceUpdateWeek();
        }
    },
    mounted() {
        axios.get("listmodules").then(response => {
            console.log(response)
            this.$store.commit('updateModules', response.data);
        })
        axios.get("getsettings").then(response => {
            console.log(response)
            this.$store.commit('setSettings', response.data);
        })
        this.$store.commit('setLoading', {module_name: 'fetchdata', loading: true});
        axios.get("fetchdata", {params: {
                parse: "0",
                from: this.$store.getters.getFrom,
                to: this.$store.getters.getTo,
            }}).then(response => {
            console.log("fetchdata (parse: 0)", response)
            this.$store.commit('updateModules', response.data);
            this.$store.commit('setLoading', {module_name: 'fetchdata', loading: false});
        })
    }
});