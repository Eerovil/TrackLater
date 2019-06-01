var home = Vue.component("home", {
    template: `
    <toolbar
        :modules="modules"
        v-on:fetchModule=fetchModule($event)
    ></toolbar>
    `,
    data() {
        return {
            modules: {}
        }
    },
    methods: {
        fetchModule(module_name) {
            console.log(`Fetching ${module_name}`)

            axios.get("fetchdata", {params: {keys: [module_name]}}).then(response => {
                console.log(response)
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