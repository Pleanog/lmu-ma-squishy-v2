import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

import router from './router'; 

import PrimeVue from 'primevue/config';
import Aura from '@primevue/themes/aura';
import 'primeicons/primeicons.css';
import { definePreset } from '@primeuix/themes';

import 'primeflex/primeflex.css'

import * as LucideIcons from 'lucide-vue-next';

import Button from "primevue/button";
import InputText from "primevue/inputtext";
import DatePicker from 'primevue/datepicker';
import FileUpload from 'primevue/fileupload';
import Tooltip from 'primevue/tooltip';
import Dropdown from 'primevue/dropdown';
import InputSwitch from 'primevue/inputswitch';
import OverlayPanel from 'primevue/overlaypanel';
import ProgressSpinner from 'primevue/progressspinner';
import Slider from "primevue/slider";
import Image from "primevue/image";
import Message from 'primevue/message';

// Custom components
import ChatBubble from "./components/ChatBubble.vue";
import MessageInput from "./components/MessageInput.vue";
import MetadataSelector from "./components/MetadataSelector.vue";
import MediaDisplay from './components/MediaDisplay.vue';


const MyPreset = definePreset(Aura,
	{
  	semantic: {
		colorScheme: {
			light: {
				primary: {
				  50: '{slate.50}',
				  100: '{slate.100}',
				  200: '{slate.200}',
				  300: '{slate.300}',
				  400: '{slate.400}',
				  500: '{slate.500}',
				  600: '{slate.600}',
				  700: '{slate.700}',
				  800: '{slate.800}',
				  900: '{slate.900}',
				  950: '{slate.950}'
				}
			  },
			  dark: {
				primary: {
				  50: '{slate.850}',
				  100: '{slate.800}',
				  200: '{slate.750}',
				  300: '{slate.700}',
				  400: '{slate.600}',
				  500: '{slate.500}',
				  600: '{slate.400}',
				  700: '{slate.300}',
				  800: '{slate.200}',
				  900: '{slate.100}',
				  950: '{slate.50}'
				}
            }
        }
    }
});

const app = createApp(App);
app.use(router);


const savedTheme = localStorage.getItem('theme');

if (savedTheme === 'dark') {
  document.documentElement.classList.add('dark');
}

app.use(PrimeVue, {
	theme: {
		preset: MyPreset,
		options: {
			darkModeSelector: '.dark'
		}
	}
});

for (const [key, icon] of Object.entries(LucideIcons)) {
  try {
	 if (typeof icon === 'object' && icon !== null) {
	   app.component(key, icon)
	 }
  } catch (e) {
	  console.warn(`Could not register icon: ${key}`)
  }
}

app.component('Button', Button);
app.component('InputText', InputText);
app.component('DatePicker', DatePicker);
app.component('FileUpload', FileUpload);
app.directive('tooltip', Tooltip);
app.component('Dropdown', Dropdown);
app.component('InputSwitch', InputSwitch);
app.component('OverlayPanel', OverlayPanel);
app.component('ProgressSpinner', ProgressSpinner);
app.component('Slider', Slider);
app.component('Image', Image);
app.component('Message', Message);

// Custom components
app.component('ChatBubble', ChatBubble);
app.component('MessageInput', MessageInput);
app.component('MetadataSelector', MetadataSelector);
app.component('MediaDisplay', MediaDisplay);
app.mount('#app');