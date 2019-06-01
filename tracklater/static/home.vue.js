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
      :moduleColors="moduleColors"
    ></daytimeline>
    </div>
    `,
    data() {
        return {
            modules: {}
        }
    },
    computed: {
        moduleColors() {
            let ret = {};
            for(key in this.modules){
                if (this.modules[key].capabilities.indexOf('entries') < 0) {
                    continue;
                }
                ret[key] = this.modules[key].color 
            }
            return ret;
        },
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
        }
    },
    mounted() {
        axios.get("listmodules").then(response => {
            console.log(response)
            this.modules = response.data
        })
    }
});