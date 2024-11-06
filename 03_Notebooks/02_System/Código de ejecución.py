#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import pandas as pd
from janitor import clean_names
import googlemaps
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

# progress bar
from tqdm import tqdm, tqdm_notebook
# instantiate
tqdm.pandas(desc='Progreso')

import warnings
warnings.filterwarnings('ignore')



########## FUNCIONES ##########

def calidad_de_datos(df1,df2):
    
    df_alquiler_venta=df1
    df_vivienda= df2
    
    #1. Limpiamos los nombres de variables
    clean_names(df_alquiler_venta)
    clean_names(df_vivienda)
    
    
    #2. Limpiamos espacios en blanco al final de los nombres de distritos en el dataframe de alquiler_venta.
    df_alquiler_venta.reset_index(inplace=True)
    df_alquiler_venta.distrito= df_alquiler_venta.distrito.apply(lambda x: x.rstrip())
    df_alquiler_venta.set_index('distrito',inplace=True)
    
    
    #3. Renobramos las variables que consideremos y corregimos los datos de las variables previamente a la reasignación de tipos.
        #3.1 Empezamos por el dataframe vivienda
    df_vivienda.reset_index(inplace=True)
    df_vivienda.columns=['url','direccion','precio_venta','parking','n_habitaciones','m2']
    df_vivienda.direccion= df_vivienda.direccion.str.replace('\n','')
    df_vivienda['distrito']= df_vivienda.direccion.apply(lambda x: x.split(',')[-2].strip())
    
    
        #3.2 Eliminamos todas las viviendas que sean casas o chalets
    lista_texto=('Cas','Chalet')
    lista_eliminar=df_vivienda.loc[df_vivienda.direccion.str.startswith(lista_texto)].index.to_list()
    df_vivienda.drop(index=lista_eliminar,inplace=True)
    
    
        #3.3 Corregimos los valores de las variables dirección y distrito que tengan textos incorrectos
    lista_sobrante=['Piso en ','Dúplex en ','Casa o chalet independiente en ','Ático en ','Estudio en ','Chalet adosado en ','Chalet en ']

    for i in lista_sobrante:
       df_vivienda.distrito= df_vivienda.distrito.str.replace(i,'') 

    for i in lista_sobrante:
       df_vivienda.direccion= df_vivienda.direccion.str.replace(i,'') 
    
    
        #3.4 Cambiamos la variable garaje por una dicotómica Si/No. Garaje opcional lo consideramos como No.
    def reemplazar_garaje(variable):
        if variable=='Garaje incluido':
            return'SI'
        else:
            return 'NO'

    df_vivienda.parking= df_vivienda.parking.apply(lambda x: reemplazar_garaje(x))
    
    
        #3.5 Eliminamos la moneda del texto de los precios.
    df_vivienda.precio_venta= df_vivienda.precio_venta.str.replace('€','')
    df_vivienda.precio_venta= df_vivienda.precio_venta.str.replace('.','')
    
    
        #3.6 Hay algunos registros que tienen incorrectamente asignada la variable habitaciones. 
            #Realmente no tiene valor y se le asignó en el scraping los m2.

            #Movemos el dato a su columna correspondiente y marcamos como nulo el registro para n_habitaciones asignándole 0. 
            #De esta forma podemos pasar la variable posteriormente a int y corregir los nulos en el apartado correspondiente.
        
    df_vivienda.loc[~df_vivienda.n_habitaciones.apply(lambda x: x.__contains__('hab')),'m2']= \
    df_vivienda.loc[~df_vivienda.n_habitaciones.apply(lambda x: x.__contains__('hab')),'n_habitaciones']
    
    df_vivienda.loc[~df_vivienda.n_habitaciones.apply(lambda x: x.__contains__('hab')),'n_habitaciones']='0'
    
        #3.7 Corregimos el texto de los m2.
    df_vivienda.m2= df_vivienda.m2.str.replace('m²','')
    df_vivienda.m2= df_vivienda.m2.str.replace('.','')
    
    
        #3.8 Corregimos el texto de n_habitaciones.
    df_vivienda.n_habitaciones= df_vivienda.n_habitaciones.str.replace(' hab.','')
    
    
        #3.9 Seguimos con el df_alquiler_venta
    df_alquiler_venta.precio_venta_m2= df_alquiler_venta.precio_venta_m2.str.replace(' €/m²','')
    df_alquiler_venta.precio_venta_m2= df_alquiler_venta.precio_venta_m2.str.replace('.','')
    df_alquiler_venta.precio_alquiler_m2= df_alquiler_venta.precio_alquiler_m2.str.replace(' €/m²','')
    df_alquiler_venta.precio_alquiler_m2.iloc[0]=df_alquiler_venta.precio_alquiler_m2.max()
    
    
        #3.10  pasamos a int las siguientes variables:
            #Vivienda: precio_venta, n_habitaciones, m2
            #Alquiler_venta: precio_venta_m2,precio_alquiler_m2
    for variable in ['precio_venta','n_habitaciones','m2']:
        df_vivienda[variable] = df_vivienda[variable].astype('int64')
    
    for variable in ['precio_venta_m2','precio_alquiler_m2']:
        df_alquiler_venta[variable] = df_alquiler_venta[variable].astype('int64')
    
    
    #4. Análisis de nulos
    medias_habitaciones_distrito= df_vivienda.loc[df_vivienda['n_habitaciones'] !=0] \
    .groupby('distrito')['n_habitaciones'].mean().round().astype('int64').to_dict()
    
    def habitaciones(distrito):
        return medias_habitaciones_distrito[distrito]
    
    df_vivienda.loc[df_vivienda['n_habitaciones'] ==0,'n_habitaciones']= \
    df_vivienda.loc[df_vivienda['n_habitaciones'] ==0,'distrito'].apply(habitaciones)
    
    
    
def datamart(df1,df2):
    
    df_alquiler_venta=df1
    df_vivienda= df2
    
    #1. Construímos una estructura común de distritos para ambos dataframes con el objetivo de poder hacer el join
    
    dicc_distritos={'Someso - Matogrande':'Someso - Matogrande',
    'Ensanche':'Centro - Juan Flórez - Plaza Pontevedra',
    'Ciudad Vieja - Centro':'Ciudad Vieja',
    'Riazor - Los Rosales':'Riazor - Los Rosales',
    'Cuatro Caminos - Plaza de la Cubela':'Cuatro Caminos - Plaza de la Cubela',
    'Elviña - a Zapateira':'Elviña - A Zapateira',
    'Juan Flórez-San Pablo':'Centro - Juan Flórez - Plaza Pontevedra',
    'Agra del Orzán - Ventorrillo':'Agra del Orzán - Ventorrillo - Vioño',
    'Monte Alto - Zalaeta - Atocha':'Monte Alto - Zalaeta - Atocha',
    'Sagrada Familia':'Sagrada Familia',
    'Los Castros - Castrillón':'Los Castros - Castrillón - Eiris',
    'Vioño':'Vioño',
    'Eirís':'Los Castros - Castrillón - Eiris',
    'Os Mallos':'Os Mallos',
    'Falperra-Santa Lucía':'Centro - Juan Flórez - Plaza Pontevedra',
    'Mesoiro':'Mesoiro',
    'Ciudad Jardín':'Centro - Juan Flórez - Plaza Pontevedra',
    'Paseo de los Puentes-Santa Margarita':'Centro - Juan Flórez - Plaza Pontevedra'
    }

    df_vivienda['distrito_merge']=df_vivienda.distrito.map(dicc_distritos)
    
    #2. Realizamos el join por la nueva variable construída y posteriormente la eliminamos
    
    datos_vivienda=df_vivienda.merge(right=df_alquiler_venta,how='left',left_on='distrito_merge',right_index=True)
    
    df_vivienda.drop(columns='distrito_merge',inplace=True)
    
    return datos_vivienda



def creacion_variables(df):

    datos_vivienda= df
    
    #1. Calculamos el alquiler estimado
    datos_vivienda['alquiler_estimado']=datos_vivienda.m2 *datos_vivienda.precio_alquiler_m2
    
    
    #2. Calculamos el alquiler medio por distrito
    datos_vivienda['alquiler_medio_distrito']=datos_vivienda.groupby('distrito')['alquiler_estimado'].transform('mean').round(2)
    
    
    #3. Calculamos el precio de venta medio por distrito
    datos_vivienda['precio_venta_medio_distrito']=datos_vivienda.groupby('distrito')['precio_venta'].transform('mean').round(2)
    
    
    #4.Calculamos la rentabilidad media por distrito
    def costes_compra(precio_venta):
        
        #estimamos los gastos de compra y puesta a punto
        itp=precio_venta * 0.1
        notaria=500
        registro=250
        reforma= precio_venta * 0.04
        comision_agencia=3000

        total=itp+notaria+registro+reforma+comision_agencia
        return total
    
    def calculo_coste_alquiler(precio_alquiler):

        #estimamos los gastos anuales
        comunidad_anual=600
        mantenimiento_anual=precio_alquiler *0.1*12
        seguro_hogar_anual=100
        seguro_vida=150
        seguro_impago=precio_alquiler*12*0.05
        IBI= 150

        gastos_anuales= comunidad_anual + mantenimiento_anual + seguro_hogar_anual + seguro_vida + seguro_impago +IBI

        return gastos_anuales  
    
    datos_vivienda['coste_compra_vivienda']=datos_vivienda.precio_venta.apply(lambda x: costes_compra(x))
    datos_vivienda['coste_total_vivienda']=datos_vivienda.coste_compra_vivienda+datos_vivienda.precio_venta
    datos_vivienda['coste_anual_alquiler']=datos_vivienda.alquiler_estimado.apply(lambda x: calculo_coste_alquiler(x))
    datos_vivienda['beneficios_antes_impuestos']=(datos_vivienda.alquiler_estimado*12)-(datos_vivienda.coste_anual_alquiler)
    datos_vivienda['rentabilidad_bruta']=(datos_vivienda.beneficios_antes_impuestos/datos_vivienda.coste_total_vivienda).round(3)
    datos_vivienda['rentabilidad_bruta_media_distrito']=datos_vivienda.groupby('distrito')['rentabilidad_bruta'].transform('mean').round(3)
    datos_vivienda.drop(columns=['coste_anual_alquiler','coste_total_vivienda'],inplace=True)
    
    
   #5. Calculamos el capital máximo para invertir.
    #Para ello debemos tener en cuenta tanto la entrada de la hipoteca (% no financiado) como los costes asociados 
    #a la compra del inmueble. Asumiremos que la financiación es al 80%
    
    porcentaje_financiacion= 0.8

    datos_vivienda['capital_maximo_inversion']= \
    (datos_vivienda.precio_venta * (1-porcentaje_financiacion))+datos_vivienda.coste_compra_vivienda
    
    
    #6. Añadimos datos de geolocalización (latitud, longitud y código postal)
    gmaps = googlemaps.Client(key='AIzaSyA-L1uytyPY0ba_HhzpgLcUBxEXtwzzEOM')
    
    def datos_google_maps(direccion):

        #obtenemos el json a partir de la dirección
        geocode_result =gmaps.geocode(direccion)

        #recogemos del json los datos de latitud, longitud y código postal
        lat= float(geocode_result[0]['geometry']['location']['lat'])
        lng= float(geocode_result[0]['geometry']['location']['lng'])
        cp= geocode_result[0]['address_components'][-1]['long_name']

        return lat,lng,cp
    
    datos_vivienda[['latitud','longitud','codigo_postal']]= \
    datos_vivienda.direccion.progress_apply(lambda x: datos_google_maps(x)).to_list()
    
    datos_vivienda[['latitud','longitud']]=datos_vivienda[['latitud','longitud']].astype('float')
    
    #convertimos en 0 los campos que no tengan como valor un código postal real
    lista_cp=['0','1','2','3','4','5']

    def convertir_cp(x):
        if x[0] in lista_cp:
            return x
        else:
            return '0'


    datos_vivienda.codigo_postal=datos_vivienda.codigo_postal.apply(lambda x: convertir_cp(x)).astype('int64')
    
    #cambiamos los cp 15167 y 15884 por 15190 y 15007 respectivamente
    
    datos_vivienda.loc[datos_vivienda.codigo_postal.isin([15167,15884]),'codigo_postal']= \
    datos_vivienda.loc[datos_vivienda.codigo_postal.isin([15167,15884]),'codigo_postal'] \
    .apply(lambda x: np.select([x==15167,x==15884],[15190,15007]))
    
    
    #Corregimos los valores de los registros con CP=0. 
    #Para ello buscamos el siguiente piso más cercano dentro de su mismo distrito y asignamos el CP correspondiente.
    
    def asignar_cp(registro):

        #cogemos la latitud y longitud del registro como referencia
        lat_0=registro.latitud
        lon_0=registro.longitud

        #eliminamos los resgistros con cp=0
        temp=datos_vivienda.loc[(datos_vivienda.codigo_postal!=0) & (datos_vivienda.distrito==registro.distrito)].copy()

        #creamos la función que mide la distancia
        def haversine(lat1, lon1, lat2, lon2):

            R = 6372.8 #En km, si usas millas tienes que cambiarlo por 3959.87433

            dLat = radians(lat2 - lat1)
            dLon = radians(lon2 - lon1)
            lat1 = radians(lat1)
            lat2 = radians(lat2)

            a = sin(dLat/2)**2 + cos(lat1)*cos(lat2)*sin(dLon/2)**2
            c = 2*asin(sqrt(a))

            return R * c

        #creamos una nueva variable con la distancia para cada registro
        temp['pdi_localizacion'] = temp.apply(lambda x: haversine(lat_0,lon_0,x.latitud,x.longitud),axis = 1)

        #filtramos el registro con menor distancia y recuperamos su código postal
        cp_final=list(temp.loc[temp.pdi_localizacion==temp.pdi_localizacion.min()]['codigo_postal'])[0]

        return cp_final
    
    datos_vivienda.loc[datos_vivienda.codigo_postal==0,'codigo_postal']= \
    datos_vivienda.loc[datos_vivienda.codigo_postal==0].apply(lambda registro: asignar_cp(registro),axis = 1)
    
    
    
   #7. Discretización de variables 

        #m2
    condiciones = [datos_vivienda.m2 <= 50,
               (datos_vivienda.m2>50) & (datos_vivienda.m2<= 100),
               (datos_vivienda.m2>100) & (datos_vivienda.m2 <= 150),
               (datos_vivienda.m2>150) & (datos_vivienda.m2 <= 200),
               (datos_vivienda.m2 > 200)]

    resultados = ['01_hasta_50_m2','02_entre 51_y_100_m2','03_entre_101_y_150_m2','04_entre_151_y_200_m2','05_mas_de_200_m2']

    datos_vivienda['m2_disc'] = np.select(condiciones, resultados, default = -999)
    
        #número de habitaciones
    condiciones= [datos_vivienda.n_habitaciones== 1,
               datos_vivienda.n_habitaciones==2,
               datos_vivienda.n_habitaciones==3,
               datos_vivienda.n_habitaciones==4,
               datos_vivienda.n_habitaciones> 4]

    resultados = ['01_una_hab','02_dos_hab','03_tres_hab','04_cuatro_hab','05_mas_de_cuatro_hab']

    datos_vivienda['n_habitaciones_disc'] = np.select(condiciones, resultados, default = -999)   

    
def exportar_excel(df):
    
    nombre_fichero_datos_excel='df_vivienda_coruña_final.xlsx'
    ruta_completa_excel = path +  '/02_Datos/03_Finales/' + nombre_fichero_datos_excel
    df.to_excel(ruta_completa_excel,sheet_name='Datos Vivienda Coruña')
    
    
    
    
    
########## CÓDIGO ##########    
    

#Carga de datos

print('Cargando datos...')

raiz = 'C:/Users/meu87/Documents/Python Data Science Mastery/Proyectos/'

nombre_dir = '00_Filtrado de inmuebles'

path = raiz + nombre_dir


nombre_fichero_datos_1 = 'Precio alquiler y venta Coruña.csv'
nombre_fichero_datos_2 = 'Viviendas en venta Coruña.csv'

ruta_completa_1 = path + '/02_Datos/01_Originales/' + nombre_fichero_datos_1
ruta_completa_2 = path + '/02_Datos/01_Originales/' + nombre_fichero_datos_2
    
df_alquiler_venta = pd.read_csv(ruta_completa_1,index_col=0)
df_vivienda = pd.read_csv(ruta_completa_2,index_col=0)

print('Finalizado.')

#calidad de datos
print('Calidad de datos...')
calidad_de_datos(df_alquiler_venta,df_vivienda)
print('Finalizado.')

#creación del datamart
print('Creación del datamart...')
datos_vivienda=datamart(df_alquiler_venta,df_vivienda)
print('Finalizado.')

#creación de las variables sintéticas
print('Creación de las variables sintéticas...')
creacion_variables(datos_vivienda)
print('Finalizado.')

#exportación del fichero
print('Exportando...')
exportar_excel(datos_vivienda)
print('Finalizado.')

