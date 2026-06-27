var home = Vue.component("home", {
    template: `
    <div>
    <toolbar
        class="toolbar"
        v-on:fetchModule=fetchModule($event)
        v-on:exportEntry=updateEntry($event)
        v-on:setToolbarHeight=setToolbarHeight($event)
        v-on:populateLocal=populateLocal($event)
        v-bind:style="{ height: toolbarHeight }"
    ></toolbar>
    <div
        class="toolbar-separator"
        v-bind:style="{ height: toolbarSepHeight }"
    ></div>
    <div v-if="populate.active" class="populate-progress" style="
        position: fixed; left: 0; right: 0; bottom: 0; z-index: 1000;
        background: #1e1e2e; color: #fff; padding: 8px 14px;
        box-shadow: 0 -2px 8px rgba(0,0,0,0.3); font-size: 13px;">
        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
            <span>Generating local entries with Claude Opus…</span>
            <span>{{ fmtTime(populate.elapsedSec) }} / ~{{ fmtTime(populate.etaSec) }}</span>
        </div>
        <div style="height:8px; background:#3a3a4e; border-radius:4px; overflow:hidden;">
            <div v-bind:style="{
                width: populate.progress + '%',
                height: '100%',
                background: populate.progress >= 100 ? '#4caf50' : '#7c6cff',
                transition: 'width 0.25s linear' }"></div>
        </div>
    </div>
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
            populate: {
                active: false,
                progress: 0,
                elapsedSec: 0,
                etaSec: 0,
                timer: null,
            },
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
            }).catch(() => {
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
                'start_time': this.parseTime(entry.start_time).getTime(),
                'end_time': this.parseTime(entry.end_time).getTime(),
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
                this.$store.commit('setSelectedEntry', updated_entries.find((_entry) => _entry.title === response.data.title && _entry.start_time === response.data.start_time && _entry.end_time === response.data.end_time));
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
        estimatePopulateSeconds() {
            // Each weekday is a separate Opus call (~45s at effort=low on busy
            // days); weekends are mostly empty and resolve in a few seconds.
            const from = this.$store.getters.getFrom;
            const to = this.$store.getters.getTo;
            const DAY = 24 * 3600 * 1000;
            let secs = 6;
            for (let t = from; t < to; t += DAY) {
                const dow = new Date(t).getDay(); // 0 Sun .. 6 Sat
                secs += (dow === 0 || dow === 6) ? 6 : 45;
            }
            return secs;
        },
        fmtTime(sec) {
            sec = Math.max(0, Math.round(sec));
            const m = Math.floor(sec / 60);
            const s = sec % 60;
            return m + ":" + (s < 10 ? "0" : "") + s;
        },
        startPopulateProgress() {
            this.stopPopulateProgress();
            const eta = this.estimatePopulateSeconds();
            const startedAt = Date.now();
            this.populate.active = true;
            this.populate.progress = 0;
            this.populate.elapsedSec = 0;
            this.populate.etaSec = eta;
            this.populate.timer = setInterval(() => {
                const elapsed = (Date.now() - startedAt) / 1000;
                this.populate.elapsedSec = elapsed;
                // Approach but never reach 100% until the response lands; ease off
                // past the estimate so an over-running call still creeps forward.
                const frac = elapsed / eta;
                this.populate.progress = frac < 1
                    ? Math.min(95, frac * 95)
                    : Math.min(99, 95 + (1 - Math.exp(-(frac - 1))) * 4);
            }, 250);
        },
        stopPopulateProgress(done) {
            if (this.populate.timer) {
                clearInterval(this.populate.timer);
                this.populate.timer = null;
            }
            if (done) {
                this.populate.progress = 100;
                setTimeout(() => { this.populate.active = false; }, 700);
            } else {
                this.populate.active = false;
            }
        },
        populateLocal() {
            if (!confirm(
                "Replace local entries this week with entries generated by Claude Opus " +
                "from git and ActivityWatch? (takes about " +
                this.fmtTime(this.estimatePopulateSeconds()) + ")"
            )) {
                return;
            }
            this.$store.commit('setLoading', {module_name: 'populatelocal', loading: true});
            this.startPopulateProgress();
            axios.post("populatelocal", {
                from: this.$store.getters.getFrom,
                to: this.$store.getters.getTo,
                replace_existing: true,
                engine: "claude",
            }).then(response => {
                console.log("populatelocal", response);
                this.stopPopulateProgress(true);
                this.fetchModule("local", 0);
                this.$store.commit('setLoading', {module_name: 'populatelocal', loading: false});
            }).catch((err) => {
                let msg = err.message;
                if (err.response && err.response.data) {
                    const d = err.response.data;
                    if (typeof d === 'object' && d.error) {
                        msg = d.error;
                    } else if (typeof d === 'string') {
                        try {
                            msg = JSON.parse(d).error || d;
                        } catch (e) {
                            msg = d;
                        }
                    }
                }
                this.stopPopulateProgress(false);
                alert("Fill local failed: " + (msg || "unknown error"));
                this.$store.commit('setLoading', {module_name: 'populatelocal', loading: false});
            });
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
        }).catch(() => {
            this.$store.commit('setLoading', {module_name: 'fetchdata', loading: false});
        })
    }
});