<template>
 <section class="vh-100" style="background-color: #508bfc;">
  <div class="container py-5 h-100">
    <div class="row d-flex justify-content-center align-items-center h-100">
      <div class="col-12 col-md-8 col-lg-6 col-xl-5">
        <div class="card shadow-2-strong" style="border-radius: 1rem;">
          <div class="card-body p-5 text-center">
            <form @submit.prevent="handleSubmit">
            <h3 class="mb-5">TestDesk Login</h3>

            <div class="form-outline mb-4">
              <input v-model="username" type="email" id="typeEmailX-2" class="form-control form-control-lg" />
              <label class="form-label" for="typeEmailX-2">Email</label>
            </div>

            <div class="form-outline mb-4">
              <input v-model="password" type="password" id="typePasswordX-2" class="form-control form-control-lg" />
              <label class="form-label" for="typePasswordX-2">Password</label>
            </div>

            <!-- Checkbox -->
            <div class="form-check d-flex justify-content-start mb-4">
              <input v-model="rememberMe" class="form-check-input" type="checkbox" value="" id="form1Example3" />
              <label class="form-check-label" for="form1Example3"> Запомнить меня </label>
            </div>

            <button class="btn btn-primary btn-lg btn-block" type="submit">Login</button>
            </form>
            <hr class="my-4">

          </div>
        </div>
      </div>
    </div>
  </div>
</section>
</template>



<script>
import axios from 'axios';

export default {
  name: 'UserLogin',
  data(){
    return {
      username: '',
      password: '',
      rememberMe: false,
    }
  },
  methods:{
    handleSubmit(){
      let self = this;
      axios({
        method: 'post',
        url: '/login/access-token-vue',
        data: `username=${self.username}&password=${self.password}`,
        headers: {'Content-Type': 'application/x-www-form-urlencoded'}
      })

          .then(response =>{
            console.log(response.data)
            this.$router.push('/home');
          })
          .catch(error => {
            console.log(error)
          });
    }
  }
}
</script>

<style scoped>

</style>